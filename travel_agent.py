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
# 强烈建议测试成功后，通过 .env 文件加载，不要把明文 Key 留在代码里推送到 GitHub
API_KEY_dict = {"xiaomi_key":"sk-c4u4c4wcrdrslwdht7zubc5rreizojhqfi17jfotm1gpx6ez" ,'deepseek_key':"sk-c24460f7c348437b8998a6e11670731e"}
BASE_URL_list= ["https://api.xiaomimimo.com/v1" ,"https://api.deepseek.com"]
MODEL_ID_list = ["mimo-v2.5-pro" ,"deepseek-v4-flash"]

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

user_prefer = {}
def update_user_prefer(key: str, value: str) -> str:
    user_prefer[key] = value
    return f"成功记录记忆: {key} -> {value}"

available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "update_user_prefer": update_user_prefer,
    "check_ticket_status": check_ticket_status
}

# ==========================================
# 第 4 步：底层架构 (大模型客户端 & 记忆模块)
# ==========================================
class OpenAICompatibleClient:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt, system_prompt, temp=0.1):# 生成文本，返回模型回复，prompt: 用户输入的主要提示内容，告诉模型需要做什么
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt}
        ]
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temp, stream=False
        )
        return response.choices[0].message.content


class TravelMemory:
    """
    旅行智能体的专属记忆库，负责结构化存储和提取历史轨迹
    """
    def __init__(self):
        # 内部使用列表存储字典，结构化记录每一步的类型和内容
        self.records = []

    def add_record(self, record_type: str, content: str):
        """
        向记忆中添加记录。
        可选的 record_type: 'user_query', 'agent_action', 'observation', 'critic_feedback'
        """
        self.records.append({"type": record_type, "content": content})

    def get_trajectory(self) -> str:
        """
        将结构化的记忆，翻译成大模型能看懂的连续对话轨迹
        """
        trajectory_lines = []
        for record in self.records:
            if record['type'] == 'user_query':
                trajectory_lines.append(f"用户请求: {record['content']}")
            elif record['type'] == 'agent_action':
                trajectory_lines.append(record['content']) # 直接拼入 Thought 和 Action
            elif record['type'] == 'observation':
                trajectory_lines.append(f"Observation: {record['content']}")
            elif record['type'] == 'critic_feedback':
                # 质检员的严厉警告
                trajectory_lines.append(f"Observation: 【质检警告】{record['content']} 请立刻重新审视历史 Observation，调用更正确的 Action！")
        
        return "\n".join(trajectory_lines)
        
    def clear(self):
        """清空当前记忆"""
        self.records.clear()

# ==========================================
# 第 5 步：智能体核心循环 (Agent Loop)
# ==========================================
def invoke_travel_agent(user_query: str, max_turns: int = 20) -> str:
    """供 FastAPI 调用的智能体核心引擎入口"""
    global user_prefer#声明使用全局变量user_prefer
    user_prefer.clear()#清空全局变量user_prefer中的所有内容
    
    llm = OpenAICompatibleClient(model=MODEL_ID_list[1], api_key=API_KEY_dict['deepseek_key'], base_url=BASE_URL_list[1])
    
    # 🌟 实例化记忆库，存入初始任务
    memory = TravelMemory()
    memory.add_record("user_query", user_query)
    
    last_action = ""#记录上一次的Action，用于判断是否需要触发Reflection，初始值为空字符串

    print(f"\n🚀 Agent收到任务，开始运作: {user_query}")


    for i in range(max_turns):
        print(f"🤖 Agent 正在进行第 {i+1} 轮思考...")
        memory_ctx = f"\n# 用户记忆档案:\n{user_prefer if user_prefer else '尚无记录'}"
        
        # 🌟 从记忆库优雅地提取轨迹交给大模型
        trajectory_str = memory.get_trajectory()
        llm_output = llm.generate(trajectory_str, AGENT_SYSTEM_PROMPT + memory_ctx, temp=0.1)
        
        # 格式解析
        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match: llm_output = match.group(1).strip()
        
        # 🌟 把大模型本轮的动作存入记忆
        memory.add_record("agent_action", llm_output)
        
        action_match = re.search(r"Action:\s*(.*)", llm_output, re.DOTALL)
        if not action_match: continue
        
        action_str = action_match.group(1).strip()

        # 触发 Reflection 质检
        if action_str.startswith("Finish"):
            res_match = re.match(r"Finish\[(.*)\]", action_str, re.DOTALL)
            res = res_match.group(1) if res_match else action_str.replace("Finish", "")
            
            print("🕵️‍♂️ 质检官正在严格复核最终答案...")
            # 🌟 把轨迹交给质检员
            critic_input = f"【管家历史执行轨迹】:\n{memory.get_trajectory()}\n\n【管家提交的最终答案】:\n{res}"
            feedback = llm.generate(critic_input, REFLECT_PROMPT_TEMPLATE, temp=0.0)
            
            if "[PASS]" in feedback:
                print("通过质检！")
                return res
            else:
                print("质检未通过！重新思考。")
                # 🌟 把质检员的批评存入记忆库
                memory.add_record("critic_feedback", feedback)
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

        # 🌟 把工具返回的观测结果存入记忆
        memory.add_record("observation", observation)
        
    return "【系统提示】Agent 思考达到轮数上限，未能通过最终质验证，请缩小范围后重试。"


if __name__ == "__main__":
    test_query = "你好，我想去厦门旅行倾向于古建筑，根据天气推荐几个的旅游景点。"
    result = invoke_travel_agent(test_query)
    print(f"✅ 旅行智能体:{result}")