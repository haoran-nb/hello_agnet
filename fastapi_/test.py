import sys
import io
# 🛡️ 强制 UTF-8 编码，确保 Windows/WSL 终端打印 Emoji 绝不崩溃
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import re
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from openai import OpenAI

# =====================================================================
# 🛠️ 执行层（手脚）：核心自动化工具
# =====================================================================

def download_pdf_tool(pdf_url: str, save_filename: str) -> str:
    """根据 URL 规范化下载专利/技术文档，安全保存至当前文件同级的 downloads 目录"""
    # 🌟 核心技术升级：动态获取当前 .py 文件所在的绝对目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 🌟 将 downloads 文件夹牢牢绑定在当前文件的同级
    download_dir = os.path.join(current_dir, "downloads")
    
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"📁 智能体检测：已在当前脚本同级创建下载目录: {download_dir}")
        
    # 最终的绝对保存路径
    save_path = os.path.join(download_dir, save_filename)
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        # 使用流式下载 (Stream)，防止大文件撑爆系统内存
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
        return f"【成功】文件已安全保存至本地路径: {save_path}"
    except Exception as e:
        return f"【失败】下载遭遇异常: {e}"


def send_notification_email(to_email: str, subject: str, body: str, attachment_path: str = None) -> str:
    """使用公司固定凭证自动发射邮件，支持一键挂载刚刚下载的本地附件"""
    sender_email = "3483903590@qq.com"
    auth_code = "tzrlbbftdvxzcjbf" # 你的绿色通行证
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(part)
        except Exception as e:
            return f"【半成功】邮件正文就绪，但附件挂载失败: {e}"
            
    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(sender_email, auth_code)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return f"【成功】通知邮件已安全送达目标客户邮箱: {to_email}"
    except Exception as e:
        return f"【失败】邮件发射由于网络抖动崩溃: {e}"

# =====================================================================
# 🧠 认知层（大脑）：ReAct 智能体核心引擎
# =====================================================================

# 绑定通讯录，供大模型决策后动态调用
available_tools = {
    "download_pdf_tool": download_pdf_tool,
    "send_notification_email": send_notification_email
}

def run_business_agent(user_instruction: str):
    # 初始化中枢大模型（使用你调通的 Mimo 钥匙）
    client = OpenAI(
        api_key="sk-2aa7d051539d4901a9b4f179e5777af0",       # 你的最新 DS 官方密钥
        base_url="https://api.deepseek.com/v1"               # 对应截图第一行的 base_url (OpenAI)
    )
    prompt_history = [f"用户核心指令: {user_instruction}"]
    
    # 工业级 ReAct 系统提示词：强迫 LLM 输出标准的 Thought + JSON Action 闭环
    system_prompt = """你是一个在中安质环运行的自主决策型数字员工。你拥有以下两个工具：
    1. download_pdf_tool: 下载文档。参数: pdf_url (网址), save_filename (保存文件名)。
    2. send_notification_email: 发送通知邮件。参数: to_email (收件人), subject (邮件主题), body (邮件正文), attachment_path (本地附件路径，可选)。

    【严格执行规范】
    你必须按照 ReAct（思维-行动-观察）循环工作。每轮回复只能包含一对 Thought 和 Action。
    Action 必须严格输出为合法的 JSON 格式！格式示例如下：
    Thought: 我需要先下载文件...
    Action: {"tool": "download_pdf_tool", "kwargs": {"pdf_url": "http...", "save_filename": "xxx.pdf"}}
    
    当所有链路（下载文件、发送带附件的邮件）完全成功闭环后，输出终点拦截标志：
    Action: Finish[报告主管：全自动化业务流已顺利收官！]
    """

    print("🚀 [中安质环 - 自动化智能体数字员工] 已启动...")
    
    for turn in range(5):
        print(f"\n🔄 =======【第 {turn+1} 轮：智能体深度思考中】=======")
        
        response = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "\n".join(prompt_history)}
            ],
            temperature=0.1
        )
        llm_output = response.choices[0].message.content
        print(f"🧠 大脑思考与规划输出:\n{llm_output}")
        prompt_history.append(llm_output)
        
        # 🏁 1. 终点拦截
        if "Action: Finish" in llm_output:
            print("\n🏆 =======【演示成功：Agent 全链路完美闭环】=======")
            break
            
        # 🔍 升级版：更加鲁棒的 JSON 提取正则（包容更多转义字符和空格）
        json_match = re.search(r"Action:\s*(\{.*\})", llm_output, re.DOTALL)
        if not json_match:
            obs = "Observation: 错误，大模型未输出标准 JSON 格式的 Action。"
            prompt_history.append(obs)
            continue
            
        try:
            action_data = json.loads(json_match.group(1))
            tool_name = action_data.get("tool")
            kwargs = action_data.get("kwargs", {})
            
            print(f"⚙️ 自动化执行层响应 -> 调用工具: [{tool_name}]，动态入参: {kwargs}")
            
            # 动态执行手脚函数
            if tool_name in available_tools:
                observation = available_tools[tool_name](**kwargs)
            else:
                observation = f"错误：未注册的工具 [{tool_name}]"
                
        except Exception as e:
            observation = f"错误：Action JSON 解析或执行遭遇崩溃 - {e}"
            
        print(f"👁️ 世界执行层反馈 (Observation): {observation}")
        prompt_history.append(f"Observation: {observation}")

# =====================================================================
# 🎬 现场展示终极点火
# =====================================================================
if __name__ == "__main__":
    # 模拟一个完美切中中安质环业务痛点的现场指令（使用绝对不反爬的 GitHub 测试链接）
    boss_command = (
        "帮我把 Mozilla 官方的规范化helloworld说明书下载下来，"
        "网址是: https://raw.githubusercontent.com/mozilla/pdf.js/master/examples/learning/helloworld.pdf ，"
        "保存为 '中安质环_合规指南.pdf'。"
        "确认下载成功后，把这个文件作为附件，发一封邮件汇报给 3483903590@qq.com，"
        "主题写'关于合规指南下载归档的自动化汇报'，正文向审核主管简单说明已闭环。"
    )
    
    run_business_agent(boss_command)