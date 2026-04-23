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
    # 匯入寄送受試者邀請信與研究者通知信的函數
    from core.mailer import send_survey_links, send_admin_notification 
except ImportError:
    st.error("❌ 找不到 core 模組，請確認 app.py 放在專案根目錄且 core 資料夾存在。")
    st.stop()

# --- 2. 基礎配置與問卷題目 ---
st.set_page_config(page_title="User Story 實驗系統", layout="wide")

SURVEY_QUESTIONS = [
    "Using Version B rather than Version A in my job would enable me to accomplish tasks more quickly.",
    "Using Version B rather than Version A would improve my job performance.",
    "Using Version B rather than Version A in my job would increase my productivity.",
    "Using Version B rather than Version A would enhance my effectiveness on the job.",
    "Using Version B rather than Version A would make it easier to do my job.",
    "I would find using Version B rather than Version A useful in my job.",
    "Learning to operate/edit Version B would be easy for me rather than Version A.",
    "I would find it easy to get Version B to do what I want it to do rather than Version A.",
    "My interaction with Version B would be clear and understandable rather than Version A.",
    "I would find Version B to be flexible to interact with rather than Version A.",
    "It would be easy for me to become skillful at using Version B rather than Version A.",
    "I would find Version B easy to use rather than Version A."
]

# --- 3. URL 參數自動辨識 (解決信箱點擊跳轉問題) ---
if 'init_check' not in st.session_state:
    query_params = st.query_params
    if "id" in query_params:
        exp_id = query_params["id"]
        # 統一使用 data/user_project/ 路徑
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
    survey_folder = os.path.join('data', 'survey') 
    if not os.path.exists(survey_folder):
        os.makedirs(survey_folder, exist_ok=True)
    
    # 2. 處理檔名
    email_safe = final_data['user_info']['email'].replace('@', '_at_').replace('.', '_')
    fname = os.path.join(survey_folder, f"result_{st.session_state.exp_id}_{email_safe}.json")
    
    # 3. 執行儲存
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    return fname

# 檢查 API Key (優先檢查 Streamlit Secrets)
# --- 環境判斷與 API Key 讀取 ---
def get_api_key():
    # 1. 嘗試從 Streamlit Cloud 的 Secrets 讀取 (雲端環境優先)
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        # 如果在本地端且沒有 secrets.toml，st.secrets 會噴錯，我們直接進入 except
        pass

    # 2. 如果上面失敗，嘗試從本地 .env 讀取 (本地環境)
    local_key = os.getenv("OPENAI_API_KEY")
    return local_key

# 執行讀取
api_key = get_api_key()

# 判斷目前是否在本地執行 (輔助用)
IS_LOCAL = os.getenv("STREAMLIT_SERVER_ADDRESS") is None # 雲端通常會設定 server 位址

if not api_key:
    st.error("❌ OPENAI_API_KEY 缺失！請檢查雲端 Secrets 或本地 .env 檔案。")
    st.stop()

# --- 流程 A: PM 初始設定 ---
if st.session_state.step == "PM_SETUP":
    st.header("Designing an Agile Requirements Quality Agent: A Self-Improving DSPy Framework")
    example_path = Path("data/user_story_submit_example.xlsx")
    if not example_path.exists():
        example_path.parent.mkdir(parents=True, exist_ok=True)
        df_example = pd.DataFrame([
            {"description": "As a user, I want to ... so that ..."},
            {"description": "As an admin, I need to ... to ensure ..."}
        ])
        df_example.to_excel(example_path, index=False)

    with open(example_path, "rb") as f:
        example_bytes = f.read()
    
    st.info("請先下載範例檔案，填寫完成後再於下方表單上傳。")
    st.download_button(
        "📥 下載 User Story 範例檔案 (Excel)",
        data=example_bytes,
        file_name=example_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()

    # --- 開始表單 ---
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
                
                status_msg.text("⚙️ 正在進行 Scorer Alignment...")
                prog_bar.progress(10)
                
                status_msg.text(f"🧠 DSPy 正在優化 {len(stories)} 則 User Stories，每則優化時間約30秒，請不要關閉畫面")
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
                
                # --- 核心修正：確保存放到 data/user_project/ 目錄下 ---
                target_dir = os.path.join("data", "user_project")
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                
                master_path = os.path.join(target_dir, f"master_{st.session_state.exp_id}.json")
                master_data = {
                    "project_context": project_context,
                    "results": raw_results,
                    "email_list": valid_emails
                }
                with open(master_path, "w", encoding="utf-8") as f:
                    json.dump(master_data, f, ensure_ascii=False, indent=4)
                
                prog_bar.progress(100)
                status_msg.text("✅ 優化與寄送信件完成！正在進入評估頁面...")
                
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

        if st.form_submit_button("Start Measurement Scales"):
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

    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"**Version A**\n\n{ver_a}")
    with col_b:
        st.success(f"**Version B**\n\n{ver_b}")
        
    st.divider()
    st.write("#### Measurement Scales of Perceived Usefulness and Perceived Ease of Use Survey")
    current_page_scores = []
    for q_idx, q_text in enumerate(SURVEY_QUESTIONS):
        s = st.radio(
            f"Q{q_idx+1}: {q_text}", 
            [1, 2, 3, 4, 5, 6, 7], 
            horizontal=True, 
            key=f"task_{idx}_q_{q_idx}",
            format_func=lambda x: {1:"Extremely Unlikely", 2:"Quite Unlikely", 3:"Slightly Unlikely", 4:"Neither", 5:"Slightly Likely", 6:"Quite Likely", 7:"Extremely Likely"}[x]
        )
        current_page_scores.append(s)

    c_prev, c_next = st.columns(2)
    with c_prev:
        if idx > 0 and st.button("⬅️ Previous User Story"):
            st.session_state.current_idx -= 1
            st.rerun()
    with c_next:
        label = "Finish and Submit" if idx == len(df)-1 else "Next User Story ➡️"
        if st.button(label):
            st.session_state.user_responses[idx] = current_page_scores
            if idx < len(df) - 1:
                st.session_state.current_idx += 1
                st.rerun()
            else:
                st.session_state.step = "FINAL"
                st.rerun()

# --- 流程 D: 提交與自動寄信給研究者 ---
elif st.session_state.step == "FINAL":
    st.header("🏁 填寫完成")
    st.write("感謝您的參與！您的回饋對本研究至關重要。")
    
    interview = st.checkbox("我願意參加後續訪談 (約 30-40 分鐘，將額外提供 NTD 500 訪談費)")
    
    if st.button("確認提交"):
        final_payload = {
            "exp_id": st.session_state.exp_id,
            "project_context": st.session_state.get('project_context', ""),
            "user_info": st.session_state.current_user,
            "survey_results": st.session_state.user_responses,
            "interview_interested": interview,
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 1. 將結果儲存於伺服器 data/survey/ 資料夾下
        save_json_result(final_payload)
        
        # 2. 🔥 即時同步寄送填答結果給研究者 (PM)
        with st.spinner("正在將結果同步至研究者信箱..."):
            send_admin_notification(final_payload)
        
        st.balloons()
        st.markdown("---")
        st.markdown("### ✅ 提交成功！")
        st.write(f"您的實驗代碼為：**RTD-{st.session_state.exp_id}**")
        st.write("請將此代碼截圖提供給計畫主持人(鄭慈昱)，即可完成領獎。")
        st.write("現在您可以安全地關閉此瀏覽器分頁。")