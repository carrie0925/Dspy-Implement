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
    from core.mailer import send_survey_links, send_admin_notification 
    # 匯入 INVEST 定義與維度
    from core.invest_rules import INVEST_RUBRIC_15, DIM_KEYS
except ImportError:
    st.error("❌ 找不到 core 模組，請確認 app.py 放在專案根目錄且 core 資料夾存在。")
    st.stop()

# --- 2. 基礎配置與定義 (Ambiguity & INVEST) ---
st.set_page_config(page_title="User Story 實驗系統", layout="wide")

# 定義四大模糊性 (Ambiguity) 的說明文字
AMBIGUITY_TYPES = {
    "Lexical": "Ambiguity at the level of individual words that might unconsciously exist due to words having several meanings because of etymological differences or related but different meanings.",
    "Syntactic": "Ambiguity at the sentence level that is present when a sentence can be interpreted using different grammatical structures.",
    "Semantic": "Ambiguity at the phrase (i.e., part of a sentence) or sentence level that exists if there are multiple interpretations of a phrase or sentence.",
    "Pragmatic": "Ambiguity at the phrase or sentence level that is present if the context does not clarify the intended meaning."
}

# 定義 INVEST 各維度的全名與基本定義
INVEST_FULL_NAMES = {
    "I": "Independent", "N": "Negotiable", "V": "Valuable", 
    "E": "Estimable", "S": "Small", "T": "Testable"
}

INVEST_DESCRIPTIONS = {
    "I": "The independent story is self-sufficient. An independent story can be pulled into a sprint, built, and tested without waiting for another story to be completed first. It may share databases, APIs, or services with other stories, but no other story needs to be finished before this one can move forward. If removing it from the sprint would not block or delay any other story, it is independent.",
    "N": "A negotiable story tells the team what the user needs and why it matters, without specifying how the system should deliver it. A developer reading the story should find the goal clear, but the solution open — no named technology, UI component, or system behaviors have been decided in advance. The story is a starting point for a conversation, not a specification to be implemented as written.",
    "V": "The valuable story answers the question of why this feature should exist, from the perspective of a specific user or the business, not the development team. A tester reading only the 'so that' clause should be able to name who benefits and what changes in their situation when the feature exists. A story that describes only what needs to be built is a developer task, not a user story, regardless of how it is formatted.",
    "E": "The estimable story gives the development team three things: a concrete action describing what the system must do, scope boundaries defining what is included and excluded, and acceptance conditions stating what done looks like. A developer reading the story should be able to assign a complexity estimate without consulting anyone outside the team or making assumptions not stated in the text. If two developers reading the same story independently would produce significantly different estimates, the story is not yet estimable.",
    "S": "The small story covers one user goal that a team can fully deliver within a single sprint (coded, tested, and releasable) without splitting it into separate deliverables first. A developer reading the story should be able to identify a single action with a bounded outcome, where no part of the story could be removed and still deliver independent value on its own. At the same time, a small story may represent a meaningful incremental step toward a larger user goal or desired outcome. If the story contains multiple goals that could each stand alone as separate stories, or conditions that could be built and tested independently, it needs to be broken down before entering a sprint.",
    "T": "The testable story gives a QA tester everything needed to verify the feature without interpretation or discussion. A tester reading the story should be able to identify what to observe, what action to perform, and what a passing result looks like, stated in specific terms such as a number, date, named system state, or defined threshold. In practice, these acceptance criteria may be refined through discussion among QA, the product owner, and the team, but they should ultimately be expressed in a clear and explicit form within the story. If two testers reading the same story would disagree on whether the same system output passes or fails, the acceptance criteria are not yet testable."
}

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
    survey_folder = os.path.join('data', 'survey') 
    if not os.path.exists(survey_folder):
        os.makedirs(survey_folder, exist_ok=True)
    
    email_safe = final_data['user_info']['email'].replace('@', '_at_').replace('.', '_')
    fname = os.path.join(survey_folder, f"result_{st.session_state.exp_id}_{email_safe}.json")
    
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    return fname

def get_api_key():
    try:
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY")

api_key = get_api_key()
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
                send_survey_links(valid_emails, st.session_state.exp_id)
                
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

        if st.form_submit_button("進入評估系統") :
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
    
    # --- 評估任務事前說明 ---
    st.info("""
    **📝 評估任務說明**
    
    本任務分為兩個部分，請先仔細閱讀下方對照的 **Version A (原始版本)** 與 **Version B (優化版本)**，接著進行評分：
    - **Part 1: INVEST 評估**
      依據敏捷開發的 INVEST 六大準則進行評分。請對照每個題目下方的 `1-5 分詳細評分標準`，為 A、B 兩個版本分別給出 1(最低) 到 5(最高) 的分數。
    - **Part 2: 模糊性 (Ambiguity) 評估**
      評估這兩個版本的 User Story 是否存在詞彙、語法、語義或語用上的模糊不清。請參考題目下方的定義，1 分代表「完全沒有模糊 (No ambiguity)」，5 分代表「非常模糊 (Very ambiguous)」。
    """)
    st.write("")

    # --- 雙欄固定對照 ---
    ver_a = row.get('description') or row.get('original') or "內容讀取失敗"
    ver_b = row.get('optimized_description') or row.get('rewritten') or row.get('optimized') or "優化內容讀取失敗"

    col_a, col_b = st.columns(2)
    with col_a:
        st.error(f"**Version A (Original)**\n\n{ver_a}")
    with col_b:
        st.success(f"**Version B (Optimized)**\n\n{ver_b}")
        
    st.divider()

    # --- 初始化暫存容器 ---
    invest_a_scores = {}
    invest_b_scores = {}
    amb_a_scores = {}
    amb_b_scores = {}

    # --- Part 1: INVEST 評分矩陣 ---
    st.markdown("## Part 1: INVEST Evaluation")
    st.write("請依據各維度的定義與 1-5 分的詳細標準，分別為 Version A 與 Version B 進行評分。")
    st.write("")
    
    for dim in DIM_KEYS:
        full_name = INVEST_FULL_NAMES[dim]
        # 顯示維度全名與基本定義
        st.markdown(f"### 【 {full_name} 】")
        st.write(f"**Definition:** {INVEST_DESCRIPTIONS[dim]}")
        
        # 展開式面板：顯示該維度的 1-5 分詳細 Rubric
        with st.expander(f"🔍 點此展開 {full_name} ({dim}) 的 1~5 分詳細評分標準", expanded=False):
            for score in ["1", "2", "3", "4", "5"]:
                desc = INVEST_RUBRIC_15.get(dim, {}).get(score, "N/A")
                st.markdown(f"- **Score {score}**: {desc}")

        # 評分按鈕
        c1, c2 = st.columns(2)
        with c1:
            invest_a_scores[dim] = st.radio(
                f"Version A Score:", 
                options=[1, 2, 3, 4, 5], 
                horizontal=True, 
                key=f"inv_a_{idx}_{dim}"
            )
        with c2:
            invest_b_scores[dim] = st.radio(
                f"Version B Score:", 
                options=[1, 2, 3, 4, 5], 
                horizontal=True, 
                key=f"inv_b_{idx}_{dim}"
            )
        st.markdown("<br>", unsafe_allow_html=True) # 增加題距留白

    st.divider()

    # --- Part 2: Ambiguity 評分矩陣 ---
    st.markdown("## Part 2: Ambiguity Evaluation")
    st.write("Does this user story have the following ambiguity? (1: No ambiguity ~ 5: Very ambiguous)")
    st.write("")

    for amb, desc in AMBIGUITY_TYPES.items():
        st.markdown(f"### Does this user story have **{amb}** ambiguity?")
        # 直接將定義以較淡/較小的字體顯示在題目下方
        st.caption(f"💡 **Definition:** {desc}")
        
        c1, c2 = st.columns(2)
        with c1:
            amb_a_scores[amb] = st.radio(
                f"Version A Score:", 
                options=[1, 2, 3, 4, 5], 
                horizontal=True, 
                key=f"amb_a_{idx}_{amb}"
            )
        with c2:
            amb_b_scores[amb] = st.radio(
                f"Version B Score:", 
                options=[1, 2, 3, 4, 5], 
                horizontal=True, 
                key=f"amb_b_{idx}_{amb}"
            )
        st.markdown("<br>", unsafe_allow_html=True) # 增加題距留白

    st.divider()

    # --- 換頁與提交邏輯 ---
    c_prev, c_next = st.columns(2)
    with c_prev:
        if idx > 0 and st.button("⬅️ Previous User Story"):
            st.session_state.current_idx -= 1
            st.rerun()
    with c_next:
        label = "Finish and Submit" if idx == len(df)-1 else "Next User Story ➡️"
        if st.button(label):
            # 將整理好的結構化資料存入 session_state
            st.session_state.user_responses[idx] = {
                "invest_A": invest_a_scores,
                "invest_B": invest_b_scores,
                "ambiguity_A": amb_a_scores,
                "ambiguity_B": amb_b_scores
            }
            
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
        st.write("請將此代碼截圖提供給計畫主持人，即可完成領獎。")
        st.write("現在您可以安全地關閉此瀏覽器分頁。")