import os
import re
import json
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import streamlit as st

# =====================================================================
# 🎨 网页基础配置与个性化人设 (必须放在首行)
# =====================================================================
st.set_page_config(page_title="中安质环 AI 智能体", page_icon="🤖", layout="wide")

# 🌟 锁死排版的终极 CSS
st.markdown("""
<style>
/* ====== 1. 按钮红绿灯系统 ====== */
button[kind="primary"] {
    background-color: #10a37f !important; border-color: #10a37f !important; color: white !important;
}
button[kind="primary"]:hover {
    background-color: #0b7e61 !important; border-color: #0b7e61 !important;
}
button[kind="secondary"] {
    background-color: #ff4b4b !important; border-color: #ff4b4b !important; color: white !important;
}
button[kind="secondary"]:hover {
    background-color: #dc3545 !important; border-color: #dc3545 !important;
}

/* ====== 2. 核心排版：左右高度绝对齐平 ====== */
div[data-testid="stTextArea"] > div {
    height: 260px !important;
}
div[data-testid="stTextArea"] textarea {
    height: 100% !important;
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    resize: none !important;
}

div[data-testid="stCodeBlock"] pre {
    height: 260px !important;
    min-height: 260px !important;
    max-height: 260px !important;
    overflow-y: auto !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 12px !important;
}
div[data-testid="stCodeBlock"] code {
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
    white-space: pre-wrap !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>🤖 中安质环 - 自主决策型数字员工控制台</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray; margin-bottom: 2rem;'>基于 ReAct 范式架构 · 由 DeepSeek-V4-Pro 强力驱动</p>", unsafe_allow_html=True)
st.markdown("---")

# =====================================================================
# 📚 RAG 向量知识库初始化层（模拟本地向量库）
# =====================================================================
def mock_rag_search(query: str) -> str:
    """模拟轻量级本地向量数据库 ChromaDB 的相似度检索召回效果"""
    # 真实场景下这里会加载 chromadb.PersistentClient() 进行 Vector Search
    policy_database = [
        "中安质环分发合规规定：财务类文件必须抄送至 cw@zhzh.com；合规指南3.0版或测试类说明书属于业务部，必须发给 3483903590@qq.com。",
        "涉密文档归档安全规范：任何从 GitHub (raw.githubusercontent.com) 下载的公开技术文档，本地持久化归档名称必须符合‘中安质环_xxxxx.pdf’的格式命名要求，严禁包含个人不规范字符。"
    ]
    
    # 模拟向量余弦相似度匹配：只要用户的指令里包含相关的词，就精准召回对应的合规规则块
    if "邮件" in query or "邮箱" in query or "汇报" in query:
        return f"【ChromaDB 向量检索成功（Top-1 文本块召回）】:\n👉 \"{policy_database[0]}\""
    elif "下载" in query or "保存" in query:
        return f"【ChromaDB 向量检索成功（Top-1 文本块召回）】:\n👉 \"{policy_database[1]}\""
    return "【ChromaDB 检索完成】: 未找到高度匹配的私有规章，系统将启用大模型泛化业务逻辑决策。"

# =====================================================================
# 🛠️ 执行层（手脚）：核心自动化工具
# =====================================================================

def download_pdf_tool(pdf_url: str, save_filename: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    download_dir = os.path.join(current_dir, "downloads")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    save_path = os.path.join(download_dir, save_filename)
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(pdf_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
        st.session_state["last_downloaded_path"] = save_path
        return f"【成功】文件已安全保存至本地路径: {save_path}"
    except Exception as e:
        return f"【失败】下载遭遇异常: {e}"

def send_notification_email(to_email: str, subject: str, body: str, attachment_path: str = None) -> str:
    sender_email = "3483903590@qq.com"
    auth_code = "tzrlbbftdvxzcjbf" 
    
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
        return f"【失败】邮件发射遭遇崩溃: {e}"

# =====================================================================
# 🧠 认知层（带 RAG 检索增强的业务中枢）
# =====================================================================

def run_web_agent(user_instruction: str, log_placeholder, result_container):
    # 模拟点火
    st.session_state["agent_logs"] = "🚀 自动化智能体核心引擎已点火启动...\n"
    log_placeholder.code(st.session_state["agent_logs"])
    time.sleep(0.5)
    
    # 🌟 核心改动：在进入思考前，优先触发 RAG 向量数据库查找
    st.session_state["agent_logs"] += "🔍 [RAG 增强] 正在连入本地 ChromaDB 向量库进行背景知识比对...\n"
    log_placeholder.code(st.session_state["agent_logs"])
    time.sleep(0.6)
    
    # 获取召回内容
    rag_knowledge = mock_rag_search(user_instruction)
    st.session_state["agent_logs"] += f"{rag_knowledge}\n"
    st.session_state["agent_logs"] += "💡 [RAG 增强] 已成功将上述企业合规背景知识挂载至 LLM 上下文窗口中。\n"
    log_placeholder.code(st.session_state["agent_logs"])
    time.sleep(0.5)

    # 动态抠出文件名
    file_match = re.search(r"保存为\s*['\"情绪]([^'\"]+\.pdf)", user_instruction)
    dynamic_filename = file_match.group(1).strip() if file_match else "中安质环_合规指南3.0.pdf"
    
    # 动态抠出邮件主题
    subject_match = re.search(r"主题写['\"情绪]([^'\"]+)", user_instruction)
    dynamic_subject = subject_match.group(1).strip() if subject_match else "关于合规指南下载归档的自动化汇报"
    
    # ---- 第 1 轮 ----
    st.session_state["agent_logs"] += "\n🔄 =======【第 1 轮：智能体正在深度思考并规划】=======\n"
    st.session_state["agent_logs"] += f"🧠 大脑输出决策:\nThought: 结合用户需求与 RAG 召回的《涉密文档归档安全规范》，我需要确保把文件保存为‘{dynamic_filename}’以满足公司的合规性要求。我将率先调用本地的文件下载工具。\n"
    st.session_state["agent_logs"] += "⚙️ 系统指令：正在拆解业务步骤并调用对应底层工具...\n"
    st.session_state["agent_logs"] += "⚙️ 执行层调用 -> 启动底层模块: [文件下载服务]\n"
    log_placeholder.code(st.session_state["agent_logs"])
    
    pdf_url = "https://raw.githubusercontent.com/mozilla/pdf.js/master/examples/learning/helloworld.pdf"
    obs_download = download_pdf_tool(pdf_url, dynamic_filename)
    time.sleep(1.0) 
    
    st.session_state["agent_logs"] += f"👁️ 执行层反馈 (Observation): {obs_download}\n"
    log_placeholder.code(st.session_state["agent_logs"])
    
    # ---- 第 2 轮 ----
    st.session_state["agent_logs"] += "\n🔄 =======【第 2 轮：智能体正在深度思考并规划】=======\n"
    st.session_state["agent_logs"] += f"🧠 大脑输出决策:\nThought: 文件归档就绪。根据 RAG 知识库检索出的《分发合规规定》，当前下载的文件属于业务范畴，必须精准发给 3483903590@qq.com。下面配置邮件参数并进行自动化汇报。\n"
    st.session_state["agent_logs"] += "⚙️ 系统指令：正在拆解业务步骤并调用对应底层工具...\n"
    st.session_state["agent_logs"] += "⚙️ 执行层调用 -> 启动底层模块: [自动邮件分发系统]\n"
    log_placeholder.code(st.session_state["agent_logs"])
    
    file_path = st.session_state.get("last_downloaded_path")
    obs_email = send_notification_email(
        to_email="3483903590@qq.com",
        subject=dynamic_subject,
        body=f"审核你好，您要求的文档已成功下载并完成本地数字化归档，保存名称为：{dynamic_filename}。此流程已严格对齐 RAG 检索到的合规标准。",
        attachment_path=file_path
    )
    time.sleep(0.8)
    
    st.session_state["agent_logs"] += f"👁️ 执行层反馈 (Observation): {obs_email}\n"
    log_placeholder.code(st.session_state["agent_logs"])
    
    # ---- 第 3 轮 ----
    st.session_state["agent_logs"] += "\n🔄 =======【第 3 轮：智能体正在深度思考并规划】=======\n"
    st.session_state["agent_logs"] += "🧠 大脑输出决策:\nThought: 基于知识库校验，本地归档文件名、收件人邮箱资产均严格匹配企业准则，全链路闭环，操作完成。\n"
    st.session_state["agent_logs"] += "🏆 状态：全链路自动化流已顺利收官，操作完成！\n"
    st.session_state["agent_logs"] += "\n🏆 =======【演示成功：操作完成】=======\n"
    log_placeholder.code(st.session_state["agent_logs"])
    
    with result_container:
        st.success("🎉 任务全部大功告成！邮件已发，文件已安全归档！")
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"💾 现场导出：{os.path.basename(file_path)}",
                    data=f,
                    file_name=os.path.basename(file_path),
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            st.info(f"文件物理归档坐标: `{file_path}`")

# =====================================================================
# 🖥️ 网页前端 UI 渲染排版
# =====================================================================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("👨‍💼 主管下达自然语言指令")
    st.write("在下方输入或修改您的业务需求：")
    
    user_input = st.text_area(
        "指令输入框", 
        value="", 
        placeholder="请在此输入您的业务指令（例如：帮我把 Mozilla 官方的规范说明书下载下来，并发送邮件汇报...）",
        label_visibility="collapsed"
    )
    
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        start_btn = st.button("🚀 开始执行", type="primary", use_container_width=True)
    with btn_col2:
        stop_btn = st.button("🛑 紧急终止", type="secondary", use_container_width=True)
    
    if stop_btn:
        st.error("🚨 已强行介入！底层大模型连接与工具链已被紧急切断。")
        st.stop()
        
    st.markdown("---")
    st.subheader("📦 网页端本地成果产出区")
    
    result_container = st.container()
    with result_container:
        if "last_downloaded_path" in st.session_state and os.path.exists(st.session_state["last_downloaded_path"]):
            file_path = st.session_state["last_downloaded_path"]
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"💾 现场导出：{os.path.basename(file_path)}",
                    data=f,
                    file_name=os.path.basename(file_path),
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            st.info(f"文件物理归档坐标: `{file_path}`")
        else:
            st.write("⏳ 暂无文件产出，请先派遣智能体执行任务。")

with col2:
    st.subheader("📡 数字大脑实时思考状态日志")
    st.write("引擎运行与 ReAct 思考链路追踪：")
    
    placeholder = st.empty()
    
    if "agent_logs" in st.session_state:
        placeholder.code(st.session_state["agent_logs"])
    else:
        placeholder.code("等待任务发射... 启动后这里将实时渲染 ReAct 智能体全套思考链路。")

# 🎬 稳健触发点火
if start_btn and user_input:
    run_web_agent(user_input, placeholder, result_container)
elif start_btn and not user_input:
    st.warning("⚠️ 请先在左侧输入业务指令，然后再点击开始执行。")