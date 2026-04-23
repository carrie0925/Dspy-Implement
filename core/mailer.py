# core/mailer.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json

def send_survey_links(email_list, exp_id):
    # 建議從 .env 讀取，不要硬編碼在程式裡
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD") # 注意：這是 Gmail 的「應用程式密碼」
    
    if not sender_email or not sender_password:
        print("[ERROR] 郵件設定缺失，無法寄送。")
        return

    subject = f"【學術研究】User Story 易用性實驗邀請 - ID: {exp_id}"
    
    # 這裡的連結要改成你之後部署 Streamlit 的網址
    base_url = "https://xxx.streamlit.app"          
    link = f"{base_url}/?id={exp_id}" 

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
            請點擊以下連結開始進行易用性問卷填寫：
            {link}

            您的實驗編號為：{exp_id}
            進入系統後請選擇您的 Email 以開始評估，並且在完成問卷前都不要關閉網頁
            填寫時間約30-40分鐘，填寫完畢後請將實驗編號截圖提供給計畫主持人(鄭慈昱)，即可完成填寫金領取。
            
            若有任何問題，歡迎直接回覆此信箱與我聯繫
            祝好，
            國立清華大學服務科學研究所 鄭慈昱
            
            """
            msg.attach(MIMEText(body, 'plain'))
            server.send_message(msg)
            print(f"[INFO] 郵件已寄送至: {receiver}")

        server.quit()
    except Exception as e:
        print(f"[ERROR] 郵件寄送過程出錯: {e}")

def send_admin_notification(payload):
    """將受試者的填答結果直接寄給研究者(PM)"""
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("SENDER_PASSWORD")
    # 這裡建議直接寫死你的收件信箱，或是從環境變數讀取
    receiver = os.getenv("SENDER_EMAIL") 

    if not sender or not password:
        print("[ERROR] 郵件設定缺失，無法寄送通知。")
        return

    # 建立郵件內容
    msg = MIMEMultipart()
    exp_id = payload.get("exp_id", "Unknown")
    user_email = payload.get("user_info", {}).get("email", "Unknown")
    
    msg['Subject'] = f"🔔 [新問卷回收] 實驗代碼: RTD-{exp_id} ({user_email})"
    msg['From'] = sender
    msg['To'] = receiver

    # 將填答結果轉為美化後的 JSON 字串作為內文
    body = f"收到一份新的 User Story 評估結果：\n\n"
    body += json.dumps(payload, ensure_ascii=False, indent=4)
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print(f"[INFO] 填答結果已成功寄送至 {receiver}")
    except Exception as e:
        print(f"[ERROR] 郵件寄送失敗: {e}")