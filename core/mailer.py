# core/mailer.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_survey_links(email_list, exp_id):
    # 建議從 .env 讀取，不要硬編碼在程式裡
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD") # 注意：這是 Gmail 的「應用程式密碼」
    
    if not sender_email or not sender_password:
        print("[ERROR] 郵件設定缺失，無法寄送。")
        return

    subject = f"【學術研究】User Story 易用性實驗邀請 - ID: {exp_id}"
    
    # 這裡的連結要改成你之後部署 Streamlit 的網址
    survey_url = f"http://localhost:8501/?id={exp_id}" 

    try:
        # 設定 SMTP 伺服器 (以 Gmail 為例)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)

        for receiver in email_list:
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver
            msg['Subject'] = subject

            body = f"""
            您好：
            
            感謝您參與本次 User Story 優化研究。
            請點擊以下連結開始進行 A/B 版本對照評估：
            {survey_url}
            
            您的實驗編號為：{exp_id}
            (進入系統後請選擇您的 Email 以開始評估)
            
            祝好，
            研究小組
            """
            msg.attach(MIMEText(body, 'plain'))
            server.send_message(msg)
            print(f"[INFO] 郵件已寄送至: {receiver}")

        server.quit()
    except Exception as e:
        print(f"[ERROR] 郵件寄送過程出錯: {e}")