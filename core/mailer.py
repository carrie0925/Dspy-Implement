import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import json
import time

def send_survey_links(email_list, exp_id):
    """Send experiment invitation for candidates"""
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD") 
    
    base_url = os.getenv("APP_URL", "http://localhost:8501")
    link = f"{base_url}/?id={exp_id}" 

    if not sender_email or not sender_password:
        print("[ERROR] 郵件設定缺失 (SENDER_EMAIL/SENDER_PASSWORD)，無法寄送連結。")
        return

    subject = f"【學術研究】User Story 優化實驗問卷邀請 - ID: {exp_id}"

    try:
        # 使用 TLS 模式寄送邀請信
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

【填寫須知】
1. 進入系統後，請從選單中選擇您的 Email 以開始評估。
2. 為了確保資料正確上傳，在完成問卷並看到提交成功畫面目前請不要關閉網頁。
3. 填寫時間約 30-40 分鐘。

填寫完畢後，請將最後畫面顯示的「實驗編號」截圖提供給計畫主持人 (鄭慈昱)，即可完成參與金領取手續。

若有任何問題，歡迎直接回覆此信箱與我聯繫。
祝好，

國立清華大學服務科學研究所 鄭慈昱
            """
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            server.send_message(msg)

            # avoid too frequent sending
            time.sleep(2)
            
            print(f"[INFO] 邀請信已成功寄送至: {receiver}")

        server.quit()
    except Exception as e:
        print(f"[ERROR] 邀請信寄送過程出錯: {e}")

def send_admin_notification(payload):
    """當受試者提交問卷時，立即寄送備份資料給研究者 (PM)"""
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("SENDER_PASSWORD")
    receiver = os.getenv("SENDER_EMAIL") 

    if not sender or not password:
        print("[ERROR] 郵件設定缺失，無法寄送後台通知。")
        return

    msg = MIMEMultipart()
    exp_id = payload.get("exp_id", "Unknown")
    user_email = payload.get("user_info", {}).get("email", "Unknown")
    
    msg['Subject'] = f"🔔 [新問卷回收] 實驗代碼: RTD-{exp_id} ({user_email})"
    msg['From'] = sender
    msg['To'] = receiver

   
    json_content = json.dumps(payload, ensure_ascii=False, indent=4)
    body = f"收到一份新的 User Story 評估結果：\n\n{json_content}"
    
    msg.attach(MIMEText(body, 
                        'plain', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        print(f"[INFO] 受試者資料已成功同步至研究者信箱: {receiver}")
    except Exception as e:
        print(f"[ERROR] 後台通知寄送失敗: {e}")