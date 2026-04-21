import streamlit as st
import os
import json
import uuid
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# --- 0. 環境變數預載 (必須在匯入 core 之前) ---
load_dotenv()

# --- 1. 匯入後端核心函數 ---
try:
    from core.pipeline import run_batch_optimization
    from core.mailer import send_survey_links 
except ImportError:
    st.error("❌ 找不到 core 模組，請確認 app.py 放在專案根目錄且 core 資料夾存在。")
    st.stop()

# --- 2. 基礎配置與問卷題目 ---
st.set_page_config(page_title="User Story 實驗系統", layout="wide")

SURVEY_QUESTIONS = [
    "使用 Version B 而非 Version A 能讓我更快完成工作",
    "使用 Version B 而非 Version A 能提升我的工作表現",
    "使用 Version B 而非 Version A 能增加我的生產力",
    "使用 Version B 而非 Version A 能增強我在工作上的效能",
    "使用 Version B 而非 Version A 會讓我的工作更容易執行",
    "我發現 Version B 比起 Version A 對我的工作更有用",
    "對我來說，學習操作/編輯 Version B 比 Version A 更容易",
    "我發現 Version B 比 Version A 更容易達成我想要的目的",
    "我與 Version B 的互動會比 Version A 更清晰易懂",
    "我發現 Version B 與人互動的彈性比 Version A 更高",
    "對我來說，熟練使用 Version B 比 Version A 更容易",
    "我發現 Version B 比 Version A 更容易使用"
]

# --- 3. URL 參數自動辨識 (解決信箱點擊跳轉問題) ---
if 'init_check' not in st.session_state:
    query_params = st.query_params
    if "id" in query_params:
        exp_id = query_params["id"]
        master_path = f"data/user_project/master_{exp_id}.json"
        
        if os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as f:
                master_data = json.load(f)
            
            # 將主實驗資料注入受試者的 Session
            st.session_state.results_df = pd.DataFrame(master_data["results"])
            st.session_state.email_list = master_data["email_list"]
            st.session_state.project_context = master_data["project_context"]
            st.session_state.exp_id = exp_id
            st.session_state.step = "USER_INFO" # 自動跳轉到個人資料頁
    st.session_state.init_check = True

# --- 4. 初始化 Session State ---
if 'step' not in st.session_state: st.session_state.step = "PM_SETUP"
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0
if 'user_responses' not in st.session_state: st.session_state.user_responses = {}
if 'exp_id' not in st.session_state: st.session_state.exp_id = str(uuid.uuid4())[:8]

# --- 5. 輔助函數 ---
def process_uploaded_data(file):
    """將上傳檔案轉為 pipeline 需要的格式"""
    df_temp = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    norm_stories = []
    for i, row in df_temp.iterrows():
        content = row.get('description') or row.get('content') or row.get('story') or ""
        norm_stories.append({"id": i, "description": str(content)})
    return norm_stories

def save_json_result(final_data):
    """儲存個人填答結果至 data/survey/ 資料夾"""
    # 1. 定義並確保子資料夾路徑存在
    survey_folder = os.path.join('data', 'survey') # 你也可以改成 'responses'
    if not os.path.exists(survey_folder):
        os.makedirs(survey_folder, exist_ok=True)
    
    # 2. 處理檔名
    email_safe = final_data['user_info']['email'].replace('@', '_at_').replace('.', '_')
    fname = os.path.join(survey_folder, f"result_{st.session_state.exp_id}_{email_safe}.json")
    
    # 3. 執行儲存 (加上 indent=4 實作換行)
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    return fname

# 檢查 API Key
if not os.getenv("OPENAI_API_KEY"):
    st.error("❌ OPENAI_API_KEY 缺失！請檢查 .env 檔案。")
    st.stop()

# --- 流程 A: PM 初始設定 ---
if st.session_state.step == "PM_SETUP":
    st.header("🚀 實驗啟動面版 (PM)")
    with st.form("pm_form"):
        st.subheader("1. 專案背景描述 (選填)")
        project_context = st.text_area("描述僅存於後台資料中", height=100)
        
        st.subheader("2. 參與者 Email (最多五位，請至少填寫 PM 本人)")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            m1 = st.text_input("成員 1 (PM)", placeholder="example@ntnu.edu.tw")
            m2 = st.text_input("成員 2")
            m3 = st.text_input("成員 3")
        with c_m2:
            m4 = st.text_input("成員 4")
            m5 = st.text_input("成員 5")
        
        st.subheader("3. 上傳資料")
        file = st.file_uploader("上傳 User Story 檔案 (CSV/XLSX)", type=['csv', 'xlsx'])
        
        submit_pm = st.form_submit_button("執行優化並啟動實驗")
        
        if submit_pm:
            valid_emails = [e.strip() for e in [m1, m2, m3, m4, m5] if e.strip() and "@" in e]
            
            if file and valid_emails:
                stories = process_uploaded_data(file)
                
                # 進度條與狀態顯示
                prog_bar = st.progress(0)
                status_msg = st.empty()
                
                status_msg.text("⚙️ 正在進行 Scorer Alignment (約 20%)...")
                prog_bar.progress(20)
                
                status_msg.text(f"🧠 DSPy 正在優化 {len(stories)} 則 User Stories...")
                raw_results = run_batch_optimization(
                    stories,
                    max_rounds=int(os.getenv("MAX_ROUNDS", 3)),
                    fewshot_k=int(os.getenv("FEWSHOT_K", 4)),
                    use_dspy=True
                )
                prog_bar.progress(80)
                
                status_msg.text("📧 正在寄送邀請信件至各成員信箱...")
                # 發送信件 (mailer.py 會根據 exp_id 生成帶參數的連結)
                send_survey_links(valid_emails, st.session_state.exp_id)
                
                # 儲存 Master JSON 供成員讀取
                if not os.path.exists('data'): os.makedirs('data')
                master_data = {
                    "project_context": project_context,
                    "results": raw_results,
                    "email_list": valid_emails
                }
                with open(f"data/master_{st.session_state.exp_id}.json", "w", encoding="utf-8") as f:
                    json.dump(master_data, f, ensure_ascii=False, indent=4)
                
                prog_bar.progress(100)
                status_msg.text("✅ 優化與寄送完成！正在進入評估頁面...")
                
                res_df = pd.DataFrame(raw_results)
                st.session_state.results_df = res_df.nlargest(20, 'improvement') if 'improvement' in res_df.columns else res_df.head(20)
                st.session_state.email_list = valid_emails
                st.session_state.project_context = project_context
                st.session_state.step = "USER_INFO"
                st.rerun()
            else:
                st.error("請確認已填寫有效 Email 並上傳檔案。")

# --- 流程 B: 個人背景資訊 ---
elif st.session_state.step == "USER_INFO":
    st.header("📋 個人背景資訊")
    selected_email = st.selectbox("請選擇您的 Email 以進入系統", st.session_state.email_list)
    
    with st.form("user_profile"):
        age = st.selectbox("您的年齡", ["20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60以上"])
        agile_exp = st.selectbox("您在軟體開發產業參與與敏捷開發團隊的工作經驗？", ["未滿1年", "1~2年", "3~5年", "6~10年", "10年以上"])
        doc_exp = st.selectbox("您在軟體開發接觸需求文件的實務經驗？", ["未滿1年", "1~2年", "3~5年", "6~10年", "10年以上"])
        role = st.selectbox("您在目前的敏捷開發團隊中，是擔任何種職能的人員？", ["專案經理/專案管理/產品管理", "UIUX設計師/使用者經驗訪談", "前端/後端開發工程師/系統分析師", "其他"])
        
        if st.form_submit_button("開始進行 A/B 評估"):
            st.session_state.current_user = {
                "email": selected_email, "age": age, 
                "agile_exp": agile_exp, "doc_exp": doc_exp, "role": role
            }
            st.session_state.step = "SURVEY_MODE"
            st.rerun()

# --- 流程 C: A/B 版本評估 ---
elif st.session_state.step == "SURVEY_MODE":
    df = st.session_state.results_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    st.progress((idx + 1) / len(df))
    st.subheader(f"User Story 評估任務 ({idx + 1} / {len(df)})")
    
    ver_a = row.get('description') or row.get('original') or "內容讀取失敗"
    ver_b = row.get('optimized_description') or row.get('rewritten') or row.get('optimized') or "優化內容讀取失敗"
    ac_info = row.get('acceptance_criteria') or row.get('ac_test_info') or "未提供驗收標準"

    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"**Version A (原始版本)**\n\n{ver_a}")
    with col_b:
        st.success(f"**Version B (優化版本)**\n\n{ver_b}")
        with st.expander("🔍 查看詳細驗收標準 (AC) 與測試大綱"):
            st.write(ac_info)

    st.divider()
    st.write("#### 📝 易用性評估問卷")
    current_page_scores = []
    for q_idx, q_text in enumerate(SURVEY_QUESTIONS):
        s = st.radio(
            f"Q{q_idx+1}: {q_text}", 
            [1, 2, 3, 4, 5], 
            horizontal=True, 
            key=f"task_{idx}_q_{q_idx}",
            format_func=lambda x: {1:"強烈不同意", 2:"不同意", 3:"中立", 4:"同意", 5:"強烈同意"}[x]
        )
        current_page_scores.append(s)

    c_prev, c_next = st.columns(2)
    with c_prev:
        if idx > 0 and st.button("⬅️ 上一則"):
            st.session_state.current_idx -= 1
            st.rerun()
    with c_next:
        label = "完成評估並提交" if idx == len(df)-1 else "下一則 ➡️"
        if st.button(label):
            st.session_state.user_responses[idx] = current_page_scores
            if idx < len(df) - 1:
                st.session_state.current_idx += 1
                st.rerun()
            else:
                st.session_state.step = "FINAL"
                st.rerun()

# --- 流程 D: 提交與結束頁面 ---
elif st.session_state.step == "FINAL":
    st.header("🏁 評估已完成")
    st.write("感謝您的參與！您的回饋對本研究至關重要。")
    
    interview = st.checkbox("我願意參加後續訪談 (約 30-40 分鐘，將額外提供 NTD 500 訪談費)")
    
    if st.button("確認提交研究數據"):
        final_payload = {
            "exp_id": st.session_state.exp_id,
            "project_context": st.session_state.get('project_context', ""),
            "user_info": st.session_state.current_user,
            "survey_results": st.session_state.user_responses,
            "interview_interested": interview,
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_json_result(final_payload)
        
        st.balloons()
        st.markdown("---")
        st.markdown("### ✅ 提交成功！")
        st.write(f"您的實驗代碼為：**RTD-{st.session_state.exp_id}**")
        st.write("請將此代碼截圖提供給研究員，即可完成領獎。")
        st.write("現在您可以安全地關閉此瀏覽器分頁。")