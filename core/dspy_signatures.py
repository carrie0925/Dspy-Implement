from typing import Dict, List
import dspy
# 確保這裡的引用路徑正確，指向您的 invest_rules.py
from .invest_rules import INVEST_RUBRIC_15, DIM_KEYS

# -------------------------
# Build human-readable rubric text
# -------------------------

def _format_scale_lines(scale: Dict[str, str]) -> str:
    """將 1-5 分的定義轉化為易讀的字串"""
    lines = []
    # 確保依照 1 到 5 的順序排列
    for k in ["1", "2", "3", "4", "5"]:
        if k in scale:
            lines.append(f"  - [Score {k}]: {scale[k]}")
    return "\n".join(lines)

def build_invest_rubric_text() -> str:
    """
    整合各維度的指標名稱、基本定義與評分量表。
    """
    INVEST_DESCRIPTIONS = {
        "I": "Independent: The independent story is self-sufficient. An independent story can be pulled into a sprint, built, and tested without waiting for another story to be completed first. It may share databases, APIs, or services with other stories, but no other story needs to be finished before this one can move forward. If removing it from the sprint would not block or delay any other story, it is independent.",
        "N": "Negotiable: A negotiable story tells the team what the user needs and why it matters, without specifying how the system should deliver it. A developer reading the story should find the goal clear, but the solution open — no named technology, UI component, or system behaviors have been decided in advance. The story is a starting point for a conversation, not a specification to be implemented as written.",
        "V": "Valuable: The valuable story answers the question of why this feature should exist, from the perspective of a specific user or the business, not the development team. A tester reading only the 'so that' clause should be able to name who benefits and what changes in their situation when the feature exists. A story that describes only what needs to be built is a developer task, not a user story, regardless of how it is formatted.",
        "E": "The estimable story gives the development team three things: a concrete action describing what the system must do, scope boundaries defining what is included and excluded, and acceptance conditions stating what done looks like. A developer reading the story should be able to assign a complexity estimate without consulting anyone outside the team or making assumptions not stated in the text. If two developers reading the same story independently would produce significantly different estimates, the story is not yet estimable.",
        "S": "Small: The small story covers one user goal that a team can fully deliver within a single sprint (coded, tested, and releasable) without splitting it into separate deliverables first. A developer reading the story should be able to identify a single action with a bounded outcome, where no part of the story could be removed and still deliver independent value on its own. At the same time, a small story may represent a meaningful incremental step toward a larger user goal or desired outcome. If the story contains multiple goals that could each stand alone as separate stories, or conditions that could be built and tested independently, it needs to be broken down before entering a sprint.",
        "T": "Testable: The testable story gives a QA tester everything needed to verify the feature without interpretation or discussion. A tester reading the story should be able to identify what to observe, what action to perform, and what a passing result looks like, stated in specific terms such as a number, date, named system state, or defined threshold. In practice, these acceptance criteria may be refined through discussion among QA, the product owner, and the team, but they should ultimately be expressed in a clear and explicit form within the story. If two testers reading the same story would disagree on whether the same system output passes or fails, the acceptance criteria are not yet testable."
    }

    parts: List[str] = []
    for key in DIM_KEYS:
        # 從 invest_rules.py 獲取 1-5 分的量表
        scale_data = INVEST_RUBRIC_15.get(key, {})
        
        # 組合該維度的區塊
        header = f"### Dimension [{key}]"
        definition = f"Definition: {INVEST_DESCRIPTIONS.get(key, 'No definition provided.')}"
        rubric = _format_scale_lines(scale_data)
        
        parts.append(f"{header}\n{definition}\nScoring Rubric:\n{rubric}")
    
    return "\n\n".join(parts)

# 預先生成完整的參考文本
RUBRIC_TEXT = build_invest_rubric_text()

# -------------------------
# Define Structured Signatures
# -------------------------

class InvestScoreSig(dspy.Signature):
    """
    Evaluate a User Story based on the INVEST criteria.
    You must refer to the 'Definition' to understand the dimension's goal 
    and use the 'Scoring Rubric' to assign a precise score (1-5).
    """
    input_text = dspy.InputField(desc="The User Story text to be evaluated.")
    rubric_text = dspy.InputField(desc="The complete INVEST definitions and scoring scales.")
    
    # 強調輸出格式為 JSON，並包含分數與原因
    result_json = dspy.OutputField(desc="JSON string with keys: 'scores' (dict of I-T scores) and 'reasonings' (dict of explanations).")

class InvestRewriteSig(dspy.Signature):
    """
    Rewrite the User Story to resolve Requirements Technical Debt (RTD).
    Improve the dimensions listed in 'low_dims_csv' based on the 'suggestions'.
    """
    input_text = dspy.InputField(desc="Original User Story text.")
    low_dims_csv = dspy.InputField(desc="Comma-separated dimensions that scored low (e.g., 'S, T').")
    suggestions = dspy.InputField(desc="Specific suggestions for improvement.")
    
    refined_story = dspy.OutputField(desc="The improved, high-quality version of the User Story.")
    explanation = dspy.OutputField(desc="Briefly explain what changes were made.")