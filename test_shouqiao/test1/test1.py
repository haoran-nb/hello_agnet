import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os

def send_qq_email(to_email, subject, body, attachment_path=None):
    """
    使用QQ邮箱自动发射邮件的核心生产模块
    """
    # 🔒 已经完美填装你提供的真实鉴权凭证
    sender_email = "3483903590@qq.com"
    auth_code = "tzrlbbftdvxzcjbf" 
    
    # 1. 组装 HTTP/SMTP 邮件快递盒
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # 2. 塞入纯文本正文（指定 utf-8 彻底杜绝中文乱码）
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # 3. 动态检测并挂载附件（未来下载下来的专利通知书 PDF）
    if attachment_path and os.path.exists(attachment_path):
        try:
            with open(attachment_path, "rb") as f:
                # 读取文件的二进制流
                part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
                # 写入标准附件头部，防止中文文件名被邮件客户端强行截断或显示乱码
                part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(attachment_path))
                msg.attach(part)
                print(f"📎 成功挂载目标附件: {os.path.basename(attachment_path)}")
        except Exception as e:
            print(f"⚠️ 附件挂载遭遇异常: {e}")
            
    # 4. 连接腾讯 QQ 邮件加密服务器并强行发射
    try:
        # QQ邮箱专用的高安全级 SSL 端口是 465
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        # 拿着你的授权码登录后厨
        server.login(sender_email, auth_code)
        # 轰炸发送
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        print("🚀 [SUCCESS] 自动化邮件已成功突破网络，送达目标邮箱！")
    except Exception as e:
        print(f"💥 [ERROR] 邮件发射失败，请检查网络或授权码状态。错误报告: {e}")


# ==========================================
# 🧪 现成可用的本地验证直通车（运行即可看效果）
# ==========================================
if __name__ == "__main__":
    print("🎬 正在启动模块一本地肉身验证...")
  
    
   
    # 触发运行
    for j in range(1,6):   
        
      
    # 【测试策略】为了安全验证，我们直接让你的QQ号自己发给自己
        test_receiver = "3483903590@qq.com" 
        test_title = "【系统自动化通知】专利归档与邮件抄送联调成功测试"
        test_content = (
        f"第{j}条邮件"
        "赵经理您好：\n\n"
        "这是由 Python 自动化脚本触发的邮件。\n"
        "系统已成功接入专利流控接口，今日份的【审查意见通知书】已在本地完成规范化归档。\n\n"
        "—— 本邮件由后厨系统自动托管发出，无需回复。")
        send_qq_email(to_email=test_receiver, subject=test_title, body=test_content)
        