import streamlit as st
import streamlit.components.v1 as components
import os
import json
import uuid
import pandas as pd
import random
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
        "en": "A independent story is self-sufficient. An independent story can be pulled into a sprint, built, and tested without waiting for another story to be completed first. It may share databases, APIs, or services with other stories, but no other story needs to be finished before this one can move forward. If removing it from the sprint would not block or delay any other story, it is independent.",
        "zh": "獨立性：一個獨立的使用者故事是自足的，代表它可以放入衝刺(Sprint) 中獨立開發、測試與交付，不需要先等待其他使用者故事完成。它可以共享既有的資料庫、API 或服務；即便其他使用者故事未先完成，它仍然可以繼續推進，不需要先完成其他任何故事。若從 Sprint 中移除此故事不會阻礙或延誤其他故事，則可視為具有獨立性"
    },
    "N": {
        "en": "A negotiable story tells the team what the user needs and why it matters, without specifying how the system should deliver it. A developer reading the story should find the goal clear, but the solution open — no named technology, UI component, or system behaviors have been decided in advance. The story is a starting point for a conversation, not a specification to be implemented as written.",
        "zh": "可協商性：具有可協商性的使用者故事，應清楚說明使用者需要什麼，以及為什麼重要，但不應過早指定系統要如何實作。開發人員讀完後應能理解目標，但仍保有討論解法的空間。也就是說，故事不應預先指定特定技術、UI 元件、工作流程或系統行為。使用者故事應是團隊對話的起點，而不是必須逐字實作的規格文件"
    },
    "V": {
        "en": "A valuable story answers the question of why this feature should exist, from the perspective of a specific user or the business, not the development team. A tester reading only the \"so that\" clause should be able to name who benefits and what changes in their situation when the feature exists. A story that describes only what needs to be built is a developer task, not a user story, regardless of how it is formatted.",
        "zh": "有價值：具有價值的使用者故事，應從特定使用者或商業需求的角度，說明這個功能為什麼值得存在，而不只是描述開發團隊要做什麼。測試人員即使只閱讀「以便（so that）」子句，應能夠判斷受益者為何人以及該功能存在時其情境會有何改變。無論敘述方式如何呈現,一則只描述「要建置什麼」的故事是開發任務,而不是使用者故事。"
    },
    "E": {
        "en": "A estimable story gives the development team three things: a concrete action describing what the system must do, scope boundaries defining what is included and excluded, and acceptance conditions stating what done looks like. A developer reading the story should be able to assign a complexity estimate without consulting anyone outside the team or making assumptions not stated in the text. If two developers reading the same story independently would produce significantly different estimates, the story is not yet estimable.",
        "zh": "可估算性：具有可估算性的使用者故事，應提供開發團隊三項資訊：系統需要執行的具體動作、工作範圍的邊界(包含與不包含的內容)，以及用來判斷「完成狀態」的驗收條件。開發人員閱讀後，應能在不詢問團隊外部人員、也不做額外假設的情況下，估算此故事的複雜度。如果兩位開發人員各自讀完同一則故事，得出的估算結果差距明顯，則該故事還不具備可估算性。"
    },
    "S": {
        "en": "A small story covers one user goal that a team can fully deliver within a single sprint (coded, tested, and releasable) without splitting it into separate deliverables first. A developer reading the story should be able to identify a single action with a bounded outcome, where no part of the story could be removed and still deliver independent value on its own. At the same time, a small story may represent a meaningful incremental step toward a larger user goal or desired outcome. If the story contains multiple goals that could each stand alone as separate stories, or conditions that could be built and tested independently, it needs to be broken down before entering a sprint.",
        "zh": "小/適切規模：使用者故事若具有適切規模，代表它聚焦於一個使用者目標，且團隊能在單一 Sprint 中完成開發、測試與交付，不需要先拆成多個交付項目。開發人員閱讀後，應能辨識出一個明確動作與有邊界的成果，而且故事裡任何一部分被拿掉，剩下的內容就無法單獨產出價值。同時，一則適切規模的故事，也可以是朝向更大使用者目標或預期成果邁進的階段性步驟。若故事包含多個可各自獨立交付的目標，或包含可分開開發與測試的條件，則應在進入 Sprint 前拆分。"
    },
    "T": {
        "en": "A testable story gives a QA tester everything needed to verify the feature without interpretation or discussion. A tester reading the story should be able to identify what to observe, what action to perform, and what a passing result looks like, stated in specific terms such as a number, date, named system state, or defined threshold. In practice, these acceptance criteria may be refined through discussion among QA, the product owner, and the team, but they should ultimately be expressed in a clear and explicit form within the story. If two testers reading the same story would disagree on whether the same system output passes or fails, the acceptance criteria are not yet testable.",
        "zh": "可測試性：可測試的故事為 QA 測試人員提供了驗證功能所需的一切資訊，不需要額外的解讀或討論。閱讀故事的測試人員應該能夠識別要觀察什麼、執行什麼動作，以及什麼樣子的結果算是通過，並以具體的術語陳述，例如數字、日期、明確命名的系統狀態或已定義的門檻值。實務上，這些驗收標準可以透過 QA、產品負責人（Product Owner）和團隊之間的討論來細化，但最終應在故事中以清晰且明確的形式表達。如果兩位閱讀相同故事的測試人員對同一個系統輸出是否合格產生分歧，則該驗收標準尚不具備可測試性。"
    }
}

# 內建 1~5 分中文輔助對照表
INVEST_RUBRIC_15_ZH = {
    "I": {
        "1": "等級 1：該故事明確地受到其他特定使用者故事阻礙，或必須等其他故事完成後才能開始，在其他故事完成之前，這個故事無法開始運作，例如：「身為使用者，我希望在新的訊息系統實施後收到通知。」",
        "2": "等級 2：該故事可以開始進行，但其核心商業規則或決策邏輯是在另一個特定故事中定義或是與其共用的。該故事依賴外部邏輯才能正確運作，開發人員無法在不參考另一個故事下，獨自閱讀此故事判斷完整的決策邏輯。例如：「身為使用者，我希望在申請折扣時，使用與會員升級流程相同的資格規格，以確保我的定價一致。」",
        "3": "等級 3：該故事描述了一個獨立的功能，但它所操作的物件、記錄或帳戶狀態，必須在生產環境前存在，才能促使這使用者故事有意義。建置工作是可以分離的，但故事仍依賴先決條件才能進行完整驗證。這種依賴關係是基於已存在的資料，而不是共用的邏輯，且只有在故事文字中明確陳述此類依賴關係時才應進行評估。例如：「身為回訪顧客，我希望檢視我過去的歷史訂單，以便我能快速重新訂購商品。」",
        "4": "等級 4：此故事可以獨立開發與實作，其依賴僅限於共用介面或服務系統元件。其他使用者故事不需先完成，且這些既有元件已足以支援開發與驗證。例如：「允許使用者透過現有的電子郵件服務重設密碼。」",
        "5": "等級 5：該故事完全自成一體；它可以獨立開發和發布，沒有阻塞性的依賴，也不需要遵守任何外部條件要求的開發順序或驗證。例如：「允許使用者變更他們的帳戶密碼。驗收條件：密碼變更流程在帳戶系統內獨立運作，不需要依賴其他功能或外部工作流程。」"
    },
    "N": {
        "1": "等級 1：該故事規定了特定的後端、架構、演算法、資料庫或技術實作細節，幾乎沒有留給團隊考慮替代解決方案的空間，這被視為可協商性的最低等級，因為它限制了底層技術設計，並可能限制了多個下游實作的選擇，例如：「身為使用者，我希望系統將我的購買記錄儲存在一個具有三個正規化資料表（訂單、項目、付款）的 MySQL 資料庫中，以便我能檢視我過去的交易。」",
        "2": "等級 2：該故事指定了一個特定的 UI 元件、互動模式或展示層的解決方案。使用者目標可能很明確，後端實作可能仍然保持開放，但介面解決方案在團隊需求釐清之前就已經決定好了。例如：「身為使用者，我希望在頂部導覽列中有一個下拉式選單來選擇我的偏好語言，以便網站以我的語言顯示。」",
        "3": "等級 3：該故事描述了特定的系統行為、回應管道或處理流程，而不是使用者的成果。沒有指定 UI 元件，但故事承諾了系統將如何運作，在有替代方案存在的情況下，指定了通知方法、工作流程步驟或處理順序。團隊可以選擇介面，但不能重新考慮行為方法。例如：「身為使用者，我希望在完成結帳後收到一封電子郵件確認信，以便我知道我的訂單已成立。」",
        "4": "等級 4：該故事清楚地陳述了使用者的目標和需求背後要解決的理由。技術實作保持開放。故事可能包含必要的限制，例如政策、合規性、無障礙性、整合或業務規則，但這些限制並未規定特定的 UI 元件、工作流程順序、演算法、資料庫設計或技術解決方案。團隊仍然有空間選擇如何實作解決方案。例如：「身為銀行客戶，我希望在檢視帳戶詳細資訊之前驗證我的身分，以確保我的財務資訊受到保護。」",
        "5": "等級 5：該故事定義了使用者需求或業務問題，而沒有暗示特定的解決方案、介面、工作流程、管道、技術或實作限制。它讓團隊能在需求釐清過程中共同創作出最合適的解法。例如：「身為銀行客戶，我希望我的帳戶詳細資訊能免於未經授權的存取，以確保我的財務資訊安全。」"
    },
    "V": {
        "1": "等級 1：描述了一項開發人員任務（例如，「重構程式碼」、「建立資料表」），且無法察覺的使用者或商業價值。例如：「重構後端程式碼。」",
        "2": "等級 2：效益子句描述了完成該動作的直接結果，也就是使用者做完該動作後當下成立的狀態，而不是解釋這個結果為什麼很重要。這裡的「以便（so that）」只是把動作換句話說，重新陳述為「已完成的狀態」、「取得存取的條件」,或「系統的確認訊息」。它只說明功能跑得起來,卻沒有說使用者因此能做什麼、能避開什麼,或能達成什麼。例如：「身為使用者，我希望提交我的工時表，以便我的工時表被提交。」「身為會員，我希望登入，以便我已登入並可以存取該網站。」「身為顧客，我希望下訂單，以便訂單在系統中被建立。」",
        "3": "等級 3：效益子句提出了一個正面的方向（例如，節省時間、改善體驗、提高效率），但沒有具體說明誰能受惠、在什麼情況下，或是與什麼基準相比。這個價值聽起來合理但很籠統：同一段「以便(so that)」子句可以挪用到待辦清單裡的好幾則故事上，讀起來都不會違和。產品團隊無法使用這種效益來排優先順序、驗證成效，或衡量這則故事的價值。例如：模糊的成果：「身為回訪顧客，我希望檢視我之前的訂單，以便我在重新訂購時能節省時間。」 體驗聲明：「身為新使用者，我希望在引導流程中有指引的設定步驟，以便體驗更輕鬆且不那麼令人困惑。」",
        "4": "等級 4：故事指定了特定的人物誌（persona），並說明具體的使用者導向效益，也就是使用者因此能做什麼、能避開什麼、或能達成什麼以前辦不到的事。這個價值足夠具體，如果移植到另一個故事上，讀起來就會違和。即使沒有明確的績效指標，使用者的成果也清楚且可執行。例如：正向收益：「身為現場技術人員，我希望可以離線存取設備手冊，以便我無需等待網路連線即可完成維修。」 避免損失：「身為作家，我希望我的草稿每兩分鐘自動儲存一次，以便在我的瀏覽器崩潰時我不會遺失工作進度。」",
        "5": "等級 5：故事清楚闡述了對特定人物誌的價值，同時也將功能與可衡量的業務成果或關鍵結果連結起來。該價值既與使用者相關，也能量化評估。例如：「身為購票者，我希望透過自助服務頁面查看我的票券狀態，以便我無需聯繫客服即可解決狀態問題；成效將以『票券狀態相關(工單狀態、問題單狀態、客服單狀態)的客服請求減少 10%』 來衡量。」"
    },
    "E": {
        "1": "等級 1：故事未指定任何具體的系統行為。它可能表達了某種期望的品質、組織目標或籠統的改善方向，但沒有描述系統應該做什麼或讓使用者能做什麼。無法單從文字中形成對這項工作的共同理解，估算無法開始。例如：「身為使用者，我希望系統更好、更可靠，以便我可以信任它。」",
        "2": "等級 2：故事指名了一個可識別的系統動作，但沒有提供範圍邊界——沒有限制、條件、格式、數量或排除事項。團隊大致知道要建置什麼，但無法針對起點和終點達成共識。開發人員之間的估算值會有很大差異，因為每個人都會假設不同的範圍邊界。例如：「身為使用者，我希望搜尋產品，以便我可以找到我需要的東西。」",
        "3": "等級 3：故事指名了一個系統動作並定義了它的主要範圍。然而，驗收條件缺失或不完整：未說明成功標準、未指定失敗路徑，或邊界案例留待推斷。團隊可以估算核心工作，但有低估的風險，因為那些尚未釐清的邊界案例，其複雜度在開發過程中才會顯現。例如：「身為使用者，我希望匯出我的報告，以便我能在系統外分析資料。」",
        "4": "等級 4：故事定義了一個具體的動作，並且明確寫出了邊界。範圍不依賴推論或領域知識，且開發人員之間可以有一致的解讀。然而，某些驗收條件、失敗情況或邊界案例尚未完全具體說明，可能需要在實作前進行後續討論。例如：「身為購物者，我希望從產品詳細資訊頁面將產品標記為最愛，以便將其儲存到我的『最愛』清單中以供稍後查看。」",
        "5": "等級 5：故事指定了具體的系統動作、明確的範圍邊界，以及足以進行可靠估算的驗收條件。這些條件涵蓋了主要的成功路徑以及最重要的失敗或邊界案例。開發人員可以僅憑故事本身來估算工作量，而無需依賴關鍵的未說明假設或外部領域知識。例如：「身為網站管理員，我希望職缺貼文在發布滿 30天後自動下架，自動取消發布，以便網站訪客不再看到過期的列表。驗收條件：系統應在 30 天後更新職缺狀態，已過期的職缺對網站訪客隱藏，但管理員仍可存取，並正確處理現有的未發布狀態和續約情境。"
    },
    "S": {
        "1": "等級 1：故事涵蓋了廣泛的功能/模組和端到端（end-to-end）的工作流程。範圍太大，無法被視為單一的用戶故事，顯然需要大幅度拆解。例如：「身為使用者，我想要一個完整的帳戶管理系統，以便我可以控制我的個人資料、安全性和偏好的所有層面。」",
        "2": "等級 2：故事在單一陳述中結合了多個獨立的使用者目標，通常由「和（AND）」、「或（OR）」或是隱含著一連串獨立的動作。每個目標都可以獨立成為一個單獨的故事。該故事必須在開發開始前進行拆分。例如：「身為使用者，我希望搜尋產品、查看產品詳細資訊並將商品儲存到願望清單中，以便我規劃購買計劃。」",
        "3": "等級 3：故事表達了單一的使用者目標，但包含多個需要分別開發與測試工作的條件，這意味著它們無法作為一個不可再分割的最小單位（atomic unit）交付。負責此故事的開發人員必須做出多個獨立的實作決策。該故事可以拆分為較小的交付項目而不會失去連貫性。例如：「身為註冊使用者，我希望在下訂單後收到確認電子郵件，並能在我的帳戶儀表板中查看訂單摘要，以便我有購買記錄。」",
        "4": "等級 4：故事透過單一的主要路徑表達單一的使用者目標。其中出現的任何變化（例如：替代輸入、次要邊界案例）都在單次開發工作中處理，不需要單獨的交付項目。該故事已準備好進入衝刺，但開發人員在實作過程中仍需做出內部排序決策。例如：「身為使用者，我希望按名稱或類別搜尋產品，以便我能快速找到我想要的東西。」",
        "5": "等級 5：此故事描述一個使用者動作，並有明確邊界的成果。它不包含額外的使用者目標、選用變體、替代管道、多種角色或可拆分的交付項目。若故事中包含條件，該條件必須是此單一動作或規則不可或缺的一部分，而不是另一個可獨立成篇的故事。（例如：「身為網站管理員，我希望發布超過 30 天的職缺能自動取消發布，以便已填補的職位不會顯示給訪客。」）"
    },
    "T": {
        "1": "等級 1：驗收完全取決於主觀判斷。故事使用了評價性語言（「直觀」、「好」、「吸引人」、「易於使用」），反映的是一種主觀看法而非系統狀態。任兩個測試人員都不會觀察到相同的事情或應用相同的標準。例如：「身為使用者，我想要一個美觀且直觀的介面，以便我享受使用該應用程式。」",
        "2": "等級 2：故事指名了使用者想要的功能或性能，但沒有描述測試人員可以觀察到的任何具體系統行為。預期行為只能從功能名稱去推測，測試人員大致知道要查驗哪個區塊，但沒有明確的輸出、狀態變更或系統回應作為目標。例如：「身為使用者，我想要一個個人化的儀表板，以便我可以快速存取我需要的內容。」",
        "3": "等級 3：故事描述了一個測試人員可以找到並觀察的具體系統行為。然而，通過條件是相對於一個未說明的標準來定義的，這個標準可以是一個比較基準點、門檻值或是一個基線，而且這些都不涵蓋故事裡。測試人員可以執行測試，但若故事中隱含的比較基準未釐清，則無法做出最終判斷。兩位觀察到相同系統輸出的測試人員，可能對其是否合格產生分歧。例如：「身為使用者，我希望當有新活動發生時我的儀表板能自動更新，以便我無需重新整理頁面即可始終看到最新資訊。」",
        "4": "等級 4：故事描述了一個可觀察的系統行為，並給出了一個通常可以理解的預期結果，但至少有一個邊界條件仍有待解釋。測試人員可以識別要驗證什麼，但仍必須對時間點、門檻值、系統狀態、使用者條件或通過/未通過的界線做出微小的假設。存在諸如「最近的」、「活躍的」、「相關的」、「快速地」或「適當的」之類的主觀描述詞，但未明確定義。例如：「身為使用者，我希望當有人回覆我的貼文時收到通知，以便我可以在對話仍然活躍（active）時進行後續追蹤。」",
        "5": "等級 5：故事使用確定性的通過／未通過標準來描述驗收條件，例如數值、日期、持續時間、命名的系統狀態、明確的規則或布林條件。主觀描述詞僅在被明確定義的情況下才是可以接受的。任何閱讀故事的測試人員對於相同的系統輸出，都會在無需討論或解讀的情況下做出相同的合格/失敗決定。例如：「身為使用者，我希望從我的儀表板中自動移除超過 7 天的通知，以便我只看到最近的活動。驗收條件：當通知的建立日期早於目前日期 7天以上時，該通知將被移除。在過去 7天內建立的通知持續顯示。」條件極度嚴謹。包含正常流程與錯誤處理，甚至可直接轉化為自動化測試腳本。"
    }
}

# --- 3. URL 參數自動辨識 ---
if 'init_check' not in st.session_state:
    query_params = st.query_params
    if "id" in query_params:
        exp_id = query_params["id"]
        
        # 修正：確保讀取時的相對路徑與 PM_SETUP 存檔時一致
        master_path = os.path.join("data", "user_project", f"master_{exp_id}.json")
        
        if os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as f:
                master_data = json.load(f)
            
            st.session_state.results_df = pd.DataFrame(master_data["results"])
            st.session_state.email_list = master_data["email_list"]
            st.session_state.project_context = master_data.get("project_context", "")
            st.session_state.exp_id = exp_id
            
            # 讀取成功，直接跳轉到背景資訊填寫頁面
            st.session_state.step = "USER_INFO" 
        else:
            st.error(f"找不到實驗代碼為 {exp_id} 的專案資料，請確認連結是否正確。")
            
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

# --- 流程 C: 版本評估 (固定A:原始, B:優化) ---
elif st.session_state.step == "SURVEY_MODE":
    df = st.session_state.results_df
    idx = st.session_state.current_idx
    row = df.iloc[idx]
    
    # 擴充原始文字的抓取範圍，把 DSPy 可能吐回來的原始文字欄位名稱都加上去
    orig_text = row.get('description') or row.get('original') or row.get('original_story') or row.get('input') or row.get('user_story') or "內容讀取失敗"
    
    opt_text = row.get('final_text') or row.get('optimized_description') or row.get('rewritten') or "優化內容讀取失敗"
    reason = row.get('correction_reason') or "系統未提供明確的修正原因"

    # 注入 CSS 動畫、右側置頂與字體縮小樣式
    st.markdown(f"""
    <style>
    /* 針對 Streamlit 左右佈局，鎖定第 2 個欄位內部的直式區塊進行置頂 */
    [data-testid="column"]:nth-of-type(2) > div, 
    [data-testid="stColumn"]:nth-of-type(2) > div {{
        position: sticky !important;
        top: 4rem !important;
        max-height: 85vh !important;
        overflow-y: auto !important;
        padding-left: 1rem;
        border-left: 2px solid #f0f2f6;
    }}
    [data-testid="column"]:nth-of-type(2) .stAlert p {{
        font-size: 0.85rem !important;
        line-height: 1.4 !important;
    }}
    .streamlit-expanderContent {{
        padding-top: 5px !important;
    }}
    
    /* 換題閃爍動畫 */
    @keyframes flashEffect_{idx} {{
        0% {{ opacity: 0.3; transform: translateY(10px); background-color: rgba(255, 250, 205, 0.4); }}
        100% {{ opacity: 1; transform: translateY(0); background-color: transparent; }}
    }}
    [data-testid="block-container"] {{
        animation: flashEffect_{idx} 0.6s ease-out;
    }}
    </style>
    """, unsafe_allow_html=True)

    # 注入 JavaScript 強制將外層視窗滾動到最上方
    components.html(
        """
        <script>
        setTimeout(function() {
            var mainContainer = window.parent.document.querySelector('.main');
            if (mainContainer) {
                mainContainer.scrollTo({top: 0, behavior: 'smooth'});
            }
            window.parent.scrollTo({top: 0, behavior: 'smooth'});
        }, 100);
        </script>
        """,
        height=0
    )

    # 右下角彈出提示 (如果是同一題重複刷新則不提示)
    if st.session_state.get('last_notified_idx') != idx:
        st.toast(f"✨ 已跳轉至第 {idx + 1} 題", icon="🚀")
        st.session_state.last_notified_idx = idx

    # --- 固定分配：Version A 為原始版本，Version B 為優化版本 ---
    ver_a = orig_text
    ver_b = opt_text
    a_is = "Original"
    b_is = "Optimized"

    st.progress((idx + 1) / len(df))
    st.subheader(f"User Story 評估問卷 ({idx + 1} / {len(df)})")
    
    col_left, col_right = st.columns([3, 1])

    # 右側：固定顯示當前 User Story 的雙版本對照
    with col_right:
        st.markdown("### User Story")
        st.info(f"**Version A (原始版本)**\n\n{ver_a}")
        st.info(f"**Version B (優化版本)**\n\n{ver_b}")
        
        st.warning(f"**💡 修正提示 (Note)**\n\n{reason}")

    # 左側：問卷核心區
    with col_left:
        st.info("""
        **📝 問卷說明**
        
        請參考右方的 **Version A (原始版本)** 與 **Version B (優化版本)**，並針對這兩個版本進行評分：
        - **Part 1: INVEST 評估**
          依據敏捷開發的 INVEST 準則進行評分。請對照每個題目下方的 1(最低)-5(最高) 詳細評分標準，為 A、B 兩個版本給分。
        - **Part 2: 模糊性 (Ambiguity) 評估**
          評估這兩個版本的 User Story 是否有任何部分不明確，或可能產生多種解釋，並提供您的建議。
        """)
        st.write("")

        invest_a_scores = {}
        invest_b_scores = {}

        # --- Part 1: INVEST 評分矩陣 ---
        st.markdown("## Part 1: INVEST Evaluation")
        st.write("")
        
        for dim in DIM_KEYS:
            full_name = INVEST_FULL_NAMES[dim]
            st.markdown(f"### 【 {full_name} 】")
            
            st.markdown(f"<div style='font-size:0.85rem; color:#444; margin-bottom: 5px;'><strong>Definition:</strong> {INVEST_DESCRIPTIONS[dim]['en']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:0.85rem; color:#2c3e50; background-color: #f0f8ff; padding: 8px; border-radius: 5px; margin-bottom: 10px;'>💡 <strong>中文輔助理解:</strong> {INVEST_DESCRIPTIONS[dim]['zh']}</div>", unsafe_allow_html=True)
            
            with st.expander(f"🔍 點此展開Level 1~5 的詳細評分標準", expanded=False):
                for score in ["1", "2", "3", "4", "5"]:
                    desc_en = INVEST_RUBRIC_15.get(dim, {}).get(score, "N/A")
                    desc_zh = INVEST_RUBRIC_15_ZH.get(dim, {}).get(score, "")
                    
                    st.markdown(f"<div style='font-size: 0.85rem; line-height: 1.4; margin-bottom: 3px;'><strong style='font-size: 0.9rem;'>Score {score}:</strong> {desc_en}</div>", unsafe_allow_html=True)
                    if desc_zh:
                        st.markdown(f"<div style='font-size: 0.8rem; color:#666; margin-left: 20px; margin-bottom: 12px;'><em>{desc_zh}</em></div>", unsafe_allow_html=True)

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
        
        amb_options = ["Yes 是", "No 否", "Not sure 不確定"]

        st.markdown("#### Version A")
        amb_a_choice = st.radio(
            "Is any part of the version A user story ambiguous or open to multiple interpretations? \n\n"
            "針對版本 A 的使用者故事是否有任何部分不明確，或可能產生多種解釋？",
            options=amb_options,
            key=f"amb_a_choice_{idx}"
        )
        amb_a_text = ""
        if amb_a_choice == "Yes 是":
            amb_a_text = st.text_area(
                "If yes, please list the ambiguous phrase and your suggestions. \n\n"
                "若上述的回答為是，請列出該段不明確的文字在以下輸入框，並列出您的修正建議：",
                key=f"amb_a_text_{idx}"
            )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### Version B")
        amb_b_choice = st.radio(
            "Is any part of the version B user story ambiguous or open to multiple interpretations? \n\n"
            "針對版本 B 的使用者故事是否有任何部分不明確，或可能產生多種解釋？",
            options=amb_options,
            key=f"amb_b_choice_{idx}"
        )
        amb_b_text = ""
        if amb_b_choice == "Yes 是":
            amb_b_text = st.text_area(
                "If yes, please list the ambiguous phrase and your suggestions. \n\n"
                "若上述的回答為是，請列出該段不明確的文字在以下輸入框，並列出您的修正建議：",
                key=f"amb_b_text_{idx}"
            )

        st.divider()

        c_prev, c_next = st.columns(2)
        with c_prev:
            if idx > 0 and st.button("⬅️ Previous User Story"):
                st.session_state.current_idx -= 1
                st.rerun()
        with c_next:
            label = "Finish and Submit" if idx == len(df)-1 else "Next User Story ➡️"
            if st.button(label):
                # --- 必填邏輯檢查 ---
                error_a = amb_a_choice == "Yes 是" and not amb_a_text.strip()
                error_b = amb_b_choice == "Yes 是" and not amb_b_text.strip()

                if error_a or error_b:
                    if error_a:
                        st.error("⚠️ 您在 Version A 選擇了『是』，請務必填寫不明確的文字與修正建議。")
                    if error_b:
                        st.error("⚠️ 您在 Version B 選擇了『是』，請務必填寫不明確的文字與修正建議。")
                else:
                    # 檢查通過，寫入資料並跳轉
                    st.session_state.user_responses[idx] = {
                        "story_id": row.get('id', idx),
                        "version_A_is": a_is,
                        "version_B_is": b_is,
                        "version_A_text": ver_a,
                        "version_B_text": ver_b,
                        "optimization_explanation": reason, 
                        "invest_A": invest_a_scores,
                        "invest_B": invest_b_scores,
                        "ambiguity_A": {
                            "has_ambiguity": amb_a_choice,
                            "suggestion": amb_a_text
                        },
                        "ambiguity_B": {
                            "has_ambiguity": amb_b_choice,
                            "suggestion": amb_b_text
                        }
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
    
    interview = st.checkbox("我願意參加後續訪談(約 30-40 分鐘，研究人員將隨機聯繫進行訪談)，訪談結束後額外提供 NTD 500 補助費)")
    
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