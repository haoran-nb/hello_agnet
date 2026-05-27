import os
import re
import datetime
import requests
import random
from tavily import TavilyClient
from openai import OpenAI

# ==========================================
# 🚨 第 1 步：配置区
# ==========================================
API_KEY = "sk-c4u4c4wcrdrslwdht7zubc5rreizojhqfi17jfotm1gpx6ez" # Xiaomi Mimo / DeepSeek
BASE_URL = "https://api.xiaomimimo.com/v1" 
MODEL_ID = "mimo-v2.5-pro" 

TAVILY_API_KEY = "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"
os.environ['TAVILY_API_KEY'] = TAVILY_API_KEY

current_date = datetime.datetime.now().strftime("%Y年%m月%d日")

# ==========================================
# 第 2 步：定义提示词大脑
# ==========================================
AGENT_SYSTEM_PROMPT = f"""
# Role: 专业智能旅行管家
你是一个具备严密逻辑推理能力的旅行专家。当前真实时间是：{current_date}。
你的目标是基于实时天气和用户偏好，为用户筛选并核实【真实有票】的旅行方案。

# 🛠️ 可用工具列表
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str, exclude: str)`: 搜索推荐旅游景点，可排除特定景点。
- `update_user_memory(key: str, value: str)`: 记录用户的偏好或特定信息。
- `check_ticket_status(attraction: str)`: 查询指定景点的实时票务状态。

# ✍️ 输出格式要求 (严格遵守)
你的每次回复必须包含一对 Thought 和 Action，格式如下：

Thought: [思考：我目前掌握了哪些信息？还需要查什么？如果上一步结果不理想，我的备选方案是什么？]
Action: function_name(arg_name="arg_value")

注意：
1. Action 必须在同一行，不得换行。
2. 参数值必须使用【双引号】包裹。
3. 任务完成时使用：Action: Finish[最终回答]

# 📋 核心决策规则
1. **记忆与状态检查**: 
   - 动作前先看【用户记忆档案】。
   - 严禁重复查询：如果 Observation 已给出结果，严禁再次调用相同工具，必须立即向下推进。

2. **票务闭环协议**: 
   - **核实义务**: 在最终推荐任何景点前，必须先调用 `check_ticket_status`。
   - **动态补位**: 若某景点售罄，严禁列入推荐名单。你必须继续寻找备选，直到确保最终推荐的有票景点【不少于 2 个】。
   - **展示规则**: 仅展示有票景点；售罄景点仅在回答末尾的“温馨提示”中告知。

3. **实体对齐 (语言协议)**: 
   - 无论搜索返回何种语言，在调用 `check_ticket_status` 和 `Finish` 时，必须统一使用【中文名称】。

4. **反死循环**: 
   - 严禁连续调用参数完全相同的工具。
"""

REFLECT_PROMPT_TEMPLATE = """
# Role: 严厉的旅游攻略终审质检员
你的任务是审查旅行管家生成的【最终答案】是否严格符合真实的【工具查询历史轨迹】。

# 💡 核心审查标准：
1. 检查历史轨迹中所有被 `check_ticket_status` 判定为【已售罄】的景点。
2. 确保这些【已售罄】的景点**绝对没有**出现在最终答案的“主推荐列表”中。
3. 如果管家把售罄景点当成有票的推荐给了用户，说明它产生了严重幻觉！

# ✍️ 输出格式限制：
- 如果答案完美合规，没有夹带售罄景点，请直接输出：[PASS]
- 如果发现漏洞，请严格按下述格式输出，不要带有任何多余的废话：
[FAIL]: 你的最终答案里包含了已经售罄的【xxx景点】，请重新检查历史记录，将其移至温馨提示，并重新寻找有票的景点补位！
"""

# ==========================================
# 第 3 步：打造工具箱
# ==========================================
def check_ticket_status(attraction: str) -> str:
    print(f"🔗 [Mock API] 正在核实票务: {attraction}...")
    mapping = {
        "forbidden city": "故宫", "temple of heaven": "天坛",
        "summer palace": "颐和园", "badaling great wall": "八达岭长城",
        "olympic park": "奥林匹克公园"
    }
    name_lower = attraction.lower().strip()
    search_target = mapping.get(name_lower, attraction)
    
    sold_out_list = ["泰山", "故宫", "上海迪士尼", "八达岭长城", "天安门广场"]
    ticket_available_list = ["黄山", "岱庙", "红门", "天外村", "颐和园", "天坛", "国家博物馆"]

    if any(item in search_target for item in sold_out_list):
        return f"【系统提示】{attraction} 今日门票已售罄！请寻找其他备选。"
    if any(item in search_target for item in ticket_available_list):
        return f"【系统提示】{attraction} 目前余票充沛，可即时预订。"
    return f"【系统提示】{attraction} 还有余票。" if random.random() < 0.7 else f"【系统提示】{attraction} 门票已售罄。"

def get_attraction(city: str, weather: str, exclude: str = "") -> str:
    tavily = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    query = f"推荐 {city} 在 {weather} 天气下最适合去的古建筑或核心旅游景点。"
    if exclude: query += f" 请绝对不要推荐以下景点（已售罄）: {exclude}。"
    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        return response.get("answer", "未找到相关景点建议。")
    except Exception as e:
        return f"错误: 搜索失败 - {e}"

def get_weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        curr = data['current_condition'][0]
        return f"{city}当前天气:{curr['weatherDesc'][0]['value']}，气温{curr['temp_C']}°C"
    except:
        return f"错误: 无法获取{city}天气。"

user_memory = {}
def update_user_memory(key: str, value: str) -> str:
    user_memory[key] = value
    return f"成功记录记忆: {key} -> {value}"

available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "update_user_memory": update_user_memory,
    "check_ticket_status": check_ticket_status
}

# ==========================================
# 第 4 步：大模型客户端类
# ==========================================
class OpenAICompatibleClient:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt, system_prompt, temp=0.1):
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ]
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temp, stream=False
        )
        return response.choices[0].message.content

# ==========================================
# 🌟 核心修改：将主循环整体包装成给外壳调用的函数
# ==========================================
def invoke_travel_agent(user_query: str, max_turns: int = 20) -> str:
    """供 FastAPI 调用的智能体核心引擎入口"""
    # 每次调用清空一次临时记忆，防止上一次请求干扰
    global user_memory
    user_memory.clear()
    
    llm = OpenAICompatibleClient(model=MODEL_ID, api_key=API_KEY, base_url=BASE_URL)
    prompt_history = [f"用户请求: {user_query}"]
    last_action = ""

    print(f"\n🚀 Agent 后厨开始运作，收到任务: {user_query}")

    for i in range(max_turns):
        print(f"🤖 Agent 正在进行第 {i+1} 轮思考...")
        memory_ctx = f"\n# 用户记忆档案:\n{user_memory if user_memory else '尚无记录'}"
        
        llm_output = llm.generate("\n".join(prompt_history), AGENT_SYSTEM_PROMPT + memory_ctx, temp=0.1)
        
        # 格式解析
        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match: llm_output = match.group(1).strip()
        
        prompt_history.append(llm_output)
        
        action_match = re.search(r"Action:\s*(.*)", llm_output, re.DOTALL)
        if not action_match: continue
        
        action_str = action_match.group(1).strip()

        # 触发 Reflection 质检
        if action_str.startswith("Finish"):
            res_match = re.match(r"Finish\[(.*)\]", action_str, re.DOTALL)
            res = res_match.group(1) if res_match else action_str.replace("Finish", "")
            
            print("🕵️‍♂️ 质检官正在严格复核最终答案...")
            critic_input = f"【管家历史执行轨迹】:\n{chr(10).join(prompt_history[:-1])}\n\n【管家提交的最终答案】:\n{res}"
            feedback = llm.generate(critic_input, REFLECT_PROMPT_TEMPLATE, temp=0.0)
            
            if "[PASS]" in feedback:
                print("✅ 通过质检！正在向外壳交付方案。")
                return res
            else:
                print("❌ 质检未通过！勒令重修。")
                prompt_history.append(f"Observation: 【质检警告】{feedback} 请立刻重新审视历史 Observation，调用更正确的 Action！")
                last_action = ""
                continue
        
        # 防结巴死循环机制
        if action_str == last_action:
            observation = "【系统严重警告】你刚刚已经执行过完全相同的 Action 了！严禁原地打转重复调用！请立刻推进到下一步！"
        else:
            last_action = action_str
            try:
                tool_name = re.search(r"(\w+)\(", action_str).group(1)
                args_str = re.search(r"\((.*)\)", action_str).group(1)
                kwargs = dict(re.findall(r'(\w+)=["\']([^"\']*)["\']', args_str))
                observation = available_tools[tool_name](**kwargs) if tool_name in available_tools else "错误: 工具不存在"
            except Exception as e:
                observation = f"错误: 解析失败 - {e}"

        prompt_history.append(f"Observation: {observation}")
        
    return "【系统提示】Agent 思考达到轮数上限，未能通过最终质验证，请缩小范围后重试。"

# 保留单机测试能力（直接运行 python travel_agent.py 依然可以本地测）
if __name__ == "__main__":
    test_query = "你好，我想去北京旅行倾向于古建筑，根据天气推荐几个的旅游景点。"
    result = invoke_travel_agent(test_query)
    print(f"\n本地测试交付结果:\n{result}")