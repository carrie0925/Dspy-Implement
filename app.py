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

# --- 2. 基礎配置與定義 (雙語化處理) ---
st.set_page_config(page_title="User Story 實驗系統", layout="wide")

# 模糊性定義 (中英雙語)
AMBIGUITY_TYPES = {
    "Lexical (詞彙模糊)": {
        "en": "Ambiguity at the level of individual words that might unconsciously exist due to words having several meanings because of etymological differences or related but different meanings.",
        "zh": "存在於單字層級的模糊性。可能因為單字本身有多種含義，導致不自覺地產生多種解釋。"
    },
    "Syntactic (語法模糊)": {
        "en": "Ambiguity at the sentence level that is present when a sentence can be interpreted using different grammatical structures.",
        "zh": "存在於句子層級的模糊性。當一個句子可以使用不同的文法結構來解釋時就會發生。"
    },
    "Semantic (語義模糊)": {
        "en": "Ambiguity at the phrase (i.e., part of a sentence) or sentence level that exists if there are multiple interpretations of a phrase or sentence.",
        "zh": "存在於短語或句子層級的模糊性。當一個短語或句子有多種解讀方式時就會發生。"
    },
    "Pragmatic (語用模糊)": {
        "en": "Ambiguity at the phrase or sentence level that is present if the context does not clarify the intended meaning.",
        "zh": "存在於短語或句子層級的模糊性。當上下文情境無法釐清作者真實意圖時就會發生。"
    }
}

# INVEST 標題
INVEST_FULL_NAMES = {
    "I": "Independent (獨立性)", 
    "N": "Negotiable (可協商性)", 
    "V": "Valuable (有價值性)", 
    "E": "Estimable (可估算性)", 
    "S": "Small (小巧性)", 
    "T": "Testable (可測試性)"
}

# INVEST 定義 (中英雙語)
INVEST_DESCRIPTIONS = {
    "I": {
        "en": "The independent story is self-sufficient. An independent story can be pulled into a sprint, built, and tested without waiting for another story to be completed first. It may share databases, APIs, or services with other stories, but no other story needs to be finished before this one can move forward. If removing it from the sprint would not block or delay any other story, it is independent.",
        "zh": "獨立的 Story 是自給自足的。它可以隨時被排入 Sprint 中開發和測試，不需要等待其他 Story 先完成。即使移除它，也不會阻礙或延遲任何其他進度。"
    },
    "N": {
        "en": "A negotiable story tells the team what the user needs and why it matters, without specifying how the system should deliver it. A developer reading the story should find the goal clear, but the solution open — no named technology, UI component, or system behaviors have been decided in advance. The story is a starting point for a conversation, not a specification to be implemented as written.",
        "zh": "可協商的 Story 告訴團隊使用者需要什麼以及為什麼重要，但不強制規定系統該如何實作（不提特定技術或 UI）。它是討論的起點，而非寫死的死板規格。"
    },
    "V": {
        "en": " The valuable story answers the question of why this feature should exist, from the perspective of a specific user or the business, not the development team. A tester reading only the \"so that\" clause should be able to name who benefits and what changes in their situation when the feature exists. A story that describes only what needs to be built is a developer task, not a user story, regardless of how it is formatted.",
        "zh": "有價值的 Story 清楚回答了「為什麼需要這個功能？」，並點出誰能受益以及改善了什麼。只寫出「系統需要做什麼」的只是開發任務，不是 User Story。"
    },
    "E": {
        "en": "The estimable story gives the development team three things: a concrete action describing what the system must do, scope boundaries defining what is included and excluded, and acceptance conditions stating what done looks like. A developer reading the story should be able to assign a complexity estimate without consulting anyone outside the team or making assumptions not stated in the text. If two developers reading the same story independently would produce significantly different estimates, the story is not yet estimable.",
        "zh": "可估算的 Story 提供了明確的動作、範圍邊界與驗收條件。開發者閱讀後不需要東猜西想，就能給出大致的工作量估算。"
    },
    "S": {
        "en": "The small story covers one user goal that a team can fully deliver within a single sprint (coded, tested, and releasable) without splitting it into separate deliverables first. A developer reading the story should be able to identify a single action with a bounded outcome, where no part of the story could be removed and still deliver independent value on its own. At the same time, a small story may represent a meaningful incremental step toward a larger user goal or desired outcome. If the story contains multiple goals that could each stand alone as separate stories, or conditions that could be built and tested independently, it needs to be broken down before entering a sprint.",
        "zh": "小巧的 Story 涵蓋了團隊可以在單一 Sprint 內完全交付（開發、測試、可發布）的單一使用者目標。如果包含了多個目標，就應該被拆分。"
    },
    "T": {
        "en": "The testable story gives a QA tester everything needed to verify the feature without interpretation or discussion. A tester reading the story should be able to identify what to observe, what action to perform, and what a passing result looks like, stated in specific terms such as a number, date, named system state, or defined threshold. In practice, these acceptance criteria may be refined through discussion among QA, the product owner, and the team, but they should ultimately be expressed in a clear and explicit form within the story. If two testers reading the same story would disagree on whether the same system output passes or fails, the acceptance criteria are not yet testable.",
        "zh": "可測試的 Story 給予 QA 測試人員明確的驗證資訊。測試人員能清楚知道要觀察什麼、做什麼動作，以及怎樣才算「通過」（例如具體的數字、狀態）。沒有模糊解釋的空間。"
    }
}

# 內建 1~5 分中文輔助對照表
INVEST_RUBRIC_15_ZH = {
    "I": {
        "1": "明確被其他特定的 Story 阻擋。在其他任務完成前無法開始。",
        "2": "可以開始，但核心決策邏輯需依賴另一個 Story，開發者無法單獨判斷。",
        "3": "功能獨立，但測試與驗證強烈依賴其他必須預先存在的資料或環境狀態。",
        "4": "可獨立開發與實作，僅有少數共享介面依賴，不影響開發進度。",
        "5": "完全獨立。可隨時被拉進 Sprint 並獨立建置與測試。"
    },
    "N": {
        "1": "寫得像死板的技術規格，直接規定了 UI 或資料庫寫法，無討論空間。",
        "2": "包含過多實作細節，高度限制了開發團隊的技術選擇。",
        "3": "團隊有一定彈性，但部分細節仍綁得太死，需要花時間與 PO 重新協商。",
        "4": "專注於價值與需求，開發團隊可自由決定如何用技術來實作。",
        "5": "極佳的對話起點。完美描述痛點，技術實作完全開放給團隊討論決定。"
    },
    "V": {
        "1": "完全看不出價值，或只是一個純後端/技術任務，對使用者無感。",
        "2": "有提到價值但非常敷衍（例如：為了讓我能做事），無法看出解決了什麼痛點。",
        "3": "可以推測出價值，但描述的受眾或帶來的改變不夠精準。",
        "4": "清楚描述特定使用者的痛點，以及此功能將如何改善現況。",
        "5": "價值論述極度強大且精準，任何人看一眼就能明白這功能為何至關重要。"
    },
    "E": {
        "1": "完全無法估算。缺乏範圍與條件，開發者無法猜測需要多少時間。",
        "2": "有大致方向，但遺漏了關鍵範圍，需做大量假設才能給出分數。",
        "3": "可給出粗估，但仍有邊緣情況需與外部人員確認才能精準估算。",
        "4": "內容清晰，包含具體動作與邊界，團隊可直接給出可靠的工作量估算。",
        "5": "極度清晰且細節完整。團隊中任何開發者獨立評估，幾乎都會給出一樣的估算。"
    },
    "S": {
        "1": "過於龐大（Epic 等級），包含太多目標，絕對無法在一個 Sprint 內做完。",
        "2": "勉強能塞進 Sprint 但風險極高，且明顯可以拆成多個獨立故事。",
        "3": "大小適中，但若仔細看，還是能進一步拆解出更小、更獨立的模塊。",
        "4": "小巧且專注於單一明確目標，可在 Sprint 輕鬆交付，且難以再拆解。",
        "5": "極度精簡專注。只包含最核心的路徑或單一條件，能極快速交付價值。"
    },
    "T": {
        "1": "沒有驗收條件，或者條件過於主觀（如：介面要好看），QA 無法測試。",
        "2": "條件模糊，缺乏具體步驟與通過標準，測試人員必須自己通靈猜測。",
        "3": "有基本驗收條件，但漏掉重要的邊緣情況（Edge cases）或具體數值限制。",
        "4": "條件明確。測試人員清楚知道要執行什麼、觀察什麼，以及怎樣算通過。",
        "5": "條件極度嚴謹。包含正常流程與錯誤處理，甚至可直接轉化為自動化測試腳本。"
    }
}

# --- 3. URL 參數自動辨識 ---
if 'init_check' not in st.session_state:
    query_params = st.query_params
    if "id" in query_params:
        exp_id = query_params["id"]
        master_path = f"/user_project/master_{exp_id}.json"
        
        if os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as f:
                master_data = json.load(f)
            
            st.session_state.results_df = pd.DataFrame(master_data["results"])
            st.session_state.email_list = master_data["email_list"]
            st.session_state.project_context = master_data["project_context"]
            st.session_state.exp_id = exp_id
            st.session_state.step = "USER_INFO" 
    st.session_state.init_check = True

# --- 4. 初始化 Session State ---
if 'step' not in st.session_state: st.session_state.step = "PM_SETUP"
if 'results_df' not in st.session_state: st.session_state.results_df = None
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0
if 'user_responses' not in st.session_state: st.session_state.user_responses = {}
if 'exp_id' not in st.session_state: st.session_state.exp_id = str(uuid.uuid4())[:8]

# --- 5. 輔助函數 ---
def process_uploaded_data(file):
    df_temp = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    norm_stories = []
    for i, row in df_temp.iterrows():
        content = row.get('description') or row.get('content') or row.get('story') or ""
        norm_stories.append({"id": i, "description": str(content)})
    return norm_stories

# 🔥 補回漏掉的資料淨化翻譯機 🔥
def safe_json_encoder(obj):
    """將 numpy 或 pandas 的資料型態轉為 Python 原生型態"""
    if hasattr(obj, 'item'):
        return obj.item()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def save_json_result(final_data):
    survey_folder = os.path.join('data', 'survey') 
    if not os.path.exists(survey_folder):
        os.makedirs(survey_folder, exist_ok=True)
    
    email_safe = final_data['user_info']['email'].replace('@', '_at_').replace('.', '_')
    fname = os.path.join(survey_folder, f"result_{st.session_state.exp_id}_{email_safe}.json")
    
    # 這裡也加上 default，雙重保險
    with open(fname, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4, default=safe_json_encoder)
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

    with st.form("pm_form"):
        st.subheader("1. 專案背景描述")
        project_context = st.text_area("此欄為選填", height=100)
        
        st.subheader("2. 參與者 Email (最多五位)")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            m1 = st.text_input("PM本人信箱", placeholder="example@gmail.com")
            m2 = st.text_input("成員 1")
            m3 = st.text_input("成員 2")
        with c_m2:
            m4 = st.text_input("成員 3")
            m5 = st.text_input("成員 4")
        
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
                
                status_msg.text(f"🧠 DSPy 正在優化 {len(stories)} 則 User Stories，每則優化時間約60秒，請不要關閉畫面")
                raw_results = run_batch_optimization(
                    stories,
                    max_rounds=int(os.getenv("MAX_ROUNDS", 3)),
                    fewshot_k=int(os.getenv("FEWSHOT_K", 4)),
                    use_dspy=True
                )
                prog_bar.progress(80)
                
                status_msg.text("📧 正在寄送邀請問卷信件至各成員信箱...")
                send_survey_links(valid_emails, st.session_state.exp_id)
                
                target_dir = os.path.join("data", "user_project")
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                
                res_df = pd.DataFrame(raw_results)
                if 'improvement' in res_df.columns:
                    survey_df = res_df.nlargest(5, 'improvement').reset_index(drop=True)
                else:
                    survey_df = res_df.head(5).reset_index(drop=True)

                master_path = os.path.join(target_dir, f"master_{st.session_state.exp_id}.json")
                master_data = {
                    "project_context": project_context,
                    "results": survey_df.to_dict('records'), 
                    "email_list": valid_emails
                }
                with open(master_path, "w", encoding="utf-8") as f:
                    json.dump(master_data, f, ensure_ascii=False, indent=4)
                
                prog_bar.progress(100)
                status_msg.text("✅ 優化與寄送信件完成！正在進入問卷填寫頁面...")
                
                st.session_state.results_df = survey_df
                st.session_state.email_list = valid_emails
                st.session_state.project_context = project_context
                st.session_state.step = "USER_INFO"
                st.rerun()
            else:
                st.error("請確認已填寫有效 Email 並上傳檔案。")

# --- 流程 B: 個人背景資訊 ---
elif st.session_state.step == "USER_INFO":
    st.header("📋 個人背景資訊")
    selected_email = st.selectbox("請選擇您的 Email", st.session_state.email_list)
    
    with st.form("user_profile"):
        age = st.selectbox("您的年齡", ["20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60以上"])
        agile_exp = st.selectbox("您參與過敏捷開發流程的專案/工作經驗（可為不連續時間段總和）？", ["6個月-1年", "1~2年", "2~3年", "3年以上"])
        doc_exp = st.selectbox("您在軟體開發接觸需求文件的實務經驗？", ["6個月-1年", "1~2年", "2~3年", "3年以上"])
        write_skill = st.selectbox("您在撰寫User Story的經驗與能力？", ["基礎", "中級", "精通"])
        lang_skill = st.selectbox("您的英文閱讀理解能力？", ["基礎", "中級", "精通"])
        role = st.selectbox("您在目前的敏捷開發團隊中，是擔任何種職能的人員？", ["專案經理/專案管理/產品管理", "UIUX設計師/使用者經驗訪談", "前端/後端開發工程師/系統分析師", "其他"])

        if st.form_submit_button("進入評估系統") :
            st.session_state.current_user = {
                "email": selected_email, "age": age, 
                "agile_exp": agile_exp, "doc_exp": doc_exp, "role": role, "write_skill": write_skill, "lang_skill": lang_skill
            }
            st.session_state.step = "SURVEY_MODE"
            st.rerun()

# --- 流程 C: A/B 版本評估 ---
elif st.session_state.step == "SURVEY_MODE":
    
    # 🔥 在這裡加上字體縮小的 CSS 🔥
    st.markdown("""
    <style>
    /* 針對 Streamlit 左右佈局，鎖定第 2 個欄位內部的直式區塊進行置頂 */
    [data-testid="column"]:nth-of-type(2) > div, 
    [data-testid="stColumn"]:nth-of-type(2) > div {
        position: sticky !important;
        top: 4rem !important;
        max-height: 85vh !important;
        overflow-y: auto !important;
        padding-left: 1rem;
        border-left: 2px solid #f0f2f6;
    }
    
    /* 針對右側欄位的提示框 (stAlert) 內的段落文字進行縮小 */
    [data-testid="column"]:nth-of-type(2) .stAlert p {
        font-size: 0.85rem !important;
        line-height: 1.4 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    df = st.session_state.results_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    # 讀取版本內容與新增的修正原因
    ver_a = row.get('description') or row.get('original') or "內容讀取失敗"
    ver_b = row.get('final_text') or row.get('optimized_description') or row.get('rewritten') or "優化內容讀取失敗"
    reason = row.get('correction_reason') or "系統未提供明確的修正原因" # [新增] 讀取 LLM 產出的修正原因

    st.progress((idx + 1) / len(df))
    st.subheader(f"User Story 模糊性品質評估問卷 ({idx + 1} / {len(df)})")
    
    col_left, col_right = st.columns([3, 1])

    # 右側：永遠固定顯示當前 User Story 的雙版本對照與優化原因
    with col_right:
        st.markdown("### User Story")
        st.error(f"**Version A (Original)**\n\n{ver_a}")
        st.success(f"**Version B (Optimized)**\n\n{ver_b}")
        
        # [新增] 顯示優化原因提示框
        st.info(f"**💡 Optimization Reason (優化原因)**\n\n{reason}")

    # 左側：問卷核心區
    with col_left:
        st.info("""
        **📝 問卷說明**
        
        請參考右方的 **Version A (原始版本)** 與 **Version B (優化版本)**，已提供中文翻譯為輔助閱讀，但實際判斷請以英文版本為各題進行評分：
        - **Part 1: INVEST 評估**
          依據敏捷開發的 INVEST 準則進行評分。請對照每個題目下方的 1(最低)-5(最高) 詳細評分標準，為 A、B 兩個版本給分。
        - **Part 2: 模糊性 (Ambiguity) 評估**
          評估這兩個版本的 User Story 是否存在詞彙(Lexical)、語法(Semantic)、語義(Syntactic)或語用(Pragmatic)上的模糊不清。1 分代表「完全沒有模糊」，5 分代表「非常模糊」。
        """)
        st.write("")

        invest_a_scores = {}
        invest_b_scores = {}
        amb_a_scores = {}
        amb_b_scores = {}

        # --- Part 1: INVEST 評分矩陣 ---
        st.markdown("## Part 1: INVEST Evaluation")
        st.write("Please rate Version A and Version B for each dimension according to the definitions and the detailed 1-5 scoring criteria.")
        st.write("")
        
        for dim in DIM_KEYS:
            full_name = INVEST_FULL_NAMES[dim]
            st.markdown(f"### 【 {full_name} 】")
            
            # 📌 雙語定義顯示
            st.caption(f"**Definition:** {INVEST_DESCRIPTIONS[dim]['en']}")
            st.info(f"💡 **中文輔助理解:** {INVEST_DESCRIPTIONS[dim]['zh']}")
            
            # 📌 展開面板：包含英文與中文的 Rubric
            with st.expander(f"🔍 點此展開 {full_name.split(' ')[0]} ({dim}) 的 1~5 分詳細評分標準", expanded=False):
                for score in ["1", "2", "3", "4", "5"]:
                    # 英文來自 core，中文來自我們內建的字典
                    desc_en = INVEST_RUBRIC_15.get(dim, {}).get(score, "N/A")
                    desc_zh = INVEST_RUBRIC_15_ZH.get(dim, {}).get(score, "")
                    
                    st.markdown(f"- **Score {score}**: {desc_en}")
                    if desc_zh:
                        st.markdown(f"<div style='color:#666; margin-left: 20px; margin-bottom:15px;'><em>{desc_zh}</em></div>", unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                invest_a_scores[dim] = st.radio(
                    f"Version A Score ({dim}):", 
                    options=[1, 2, 3, 4, 5], 
                    horizontal=True, 
                    key=f"inv_a_{idx}_{dim}"
                )
            with c2:
                invest_b_scores[dim] = st.radio(
                    f"Version B Score ({dim}):", 
                    options=[1, 2, 3, 4, 5], 
                    horizontal=True, 
                    key=f"inv_b_{idx}_{dim}"
                )
            st.markdown("<br>", unsafe_allow_html=True) 

        st.divider()

        # --- Part 2: Ambiguity 評分矩陣 ---
        st.markdown("## Part 2: Ambiguity Evaluation")
        st.write("Does this user story have the following ambiguity? (1: No ambiguity ~ 5: Very ambiguous)")
        st.write("")

        for amb_key, desc_dict in AMBIGUITY_TYPES.items():
            st.markdown(f"### Does this user story have **{amb_key}**?")
            
            # 📌 雙語定義顯示
            st.caption(f"**Definition:** {desc_dict['en']}")
            st.info(f"💡 {desc_dict['zh']}")
            
            c1, c2 = st.columns(2)
            with c1:
                amb_a_scores[amb_key.split(' ')[0]] = st.radio( 
                    f"Version A Score:", 
                    options=[1, 2, 3, 4, 5], 
                    horizontal=True, 
                    key=f"amb_a_{idx}_{amb_key}"
                )
            with c2:
                amb_b_scores[amb_key.split(' ')[0]] = st.radio( 
                    f"Version B Score:", 
                    options=[1, 2, 3, 4, 5], 
                    horizontal=True, 
                    key=f"amb_b_{idx}_{amb_key}"
                )
            st.markdown("<br>", unsafe_allow_html=True) 

        st.divider()

        c_prev, c_next = st.columns(2)
        with c_prev:
            if idx > 0 and st.button("⬅️ Previous User Story"):
                st.session_state.current_idx -= 1
                st.rerun()
        with c_next:
            label = "Finish and Submit" if idx == len(df)-1 else "Next User Story ➡️"
            if st.button(label):
                # [核心修改] 確保將 correction_reason 也存入該受試者的回應紀錄中
                st.session_state.user_responses[idx] = {
                    "story_id": row.get('id', idx),
                    "version_A_text": ver_a,
                    "version_B_text": ver_b,
                    "optimization_explanation": reason, # <--- 新增這一行，確保理由被保存
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
    st.header("填寫完成")
    st.write("感謝您的參與！您的回饋對本研究至關重要。")
    
    interview = st.checkbox("我願意參加後續訪談 (約 30-40 分鐘，研究人員將隨機聯繫進行訪談，訪談結束後額外提供 NTD 500 補助費)")
    
    if st.button("確認提交"):
        final_payload = {
            "exp_id": st.session_state.exp_id,
            "project_context": st.session_state.get('project_context', ""),
            "user_info": st.session_state.current_user,
            "survey_results": st.session_state.user_responses,
            "interview_interested": interview,
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        clean_payload = json.loads(json.dumps(final_payload, default=safe_json_encoder))
        
        save_json_result(clean_payload)
        
        with st.spinner("正在將結果同步至研究者信箱..."):
            send_admin_notification(clean_payload)
        
        st.balloons()
        st.markdown("---")
        st.markdown("### ✅ 提交成功！")
        st.write(f"您的實驗代碼為：**RTD-{st.session_state.exp_id}**")
        st.write("請將此代碼截圖提供給計畫主持人，即可完成領獎。")
        st.write("現在您可以安全地關閉此瀏覽器分頁。")