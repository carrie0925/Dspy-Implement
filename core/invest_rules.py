# -*- coding: utf-8 -*-
"""
invest_rules.py — 1–5 scale version (for assertion_rules.py Route B)

Purpose
-------
- Provide INVEST_RUBRIC_15 textual definitions for 1–5 scale.
- Provide helper function `get_invest_rubric_text()` for retrieval.
- Centralize rubric content to keep logic decoupled from assertions.

Author: YOU
"""

# --- Dimensions ---------------------------------------------------------------
DIM_KEYS = ["I", "N", "V", "E", "S"]

# --- INVEST Rubric (1–5 Scale) ------------------------------------------------
INVEST_RUBRIC_15 = {
    "I": {
        1: "The construction start of this user story is absolutely tied to the completion of at least one other user story.",
        2: "The completion of this user story hinders the start of construction of at least one other user story.",
        3: "The user story contains certain constraints, but its release is only constrained by the completion of at least one other user story.",
        4: "The user story is fully independent and can be realized and released with any constraint.",
        5: "The user story demonstrates optimal deployment independence; it is ideal for immediate and flexible delivery with zero inherent dependencies.",
    },
    "N": {
        1: "The user story contains enough detail to be a technical specification, leaving no room to negotiate any element.",
        2: "The user story is written with enough detail to be a functional specification (Analysis phase), leaving no room to negotiate any element.",
        3: "The user story is written with informative content defining a User Requirement in a consolidated manner, yet shared between Customer and Provider.",
        4: "The user story is written with the informative content typical of a high-level need, fully allowing feedback and negotiation between Customer and Provider.",
        5: "The user story perfectly defines the high-level need, maximizing implementation flexibility while explicitly preventing premature scope creep.",
    },
    "V": {
        1: "The functional part (F) of the user story does not contain all the functionalities requested by the customer.",
        2: "The functional (F) part primarily expresses qualitative (Q) and technical (T) requirements, requiring significant development in terms of functional requirements.",
        3: "The functional (F) part mostly expresses the functional requirements requested by the customer, but also includes qualitative (Q) and technical (T) requirements.",
        4: "The functional (F) part of the user story correctly expresses only the functional requirements requested by the customer.",
        5: "The value is quantifiable and perfectly aligned with a measurable business outcome or clear user benefit, exceeding mere functional correctness.",
    },
    "E": {
        1: "The user story shows only its functional (F) part, filled in by the customer, without sufficient detail to allow the provider to fill in the Q/T parts.",
        2: "The user story shows only its functional (F) part, filled in by the customer, but the content has been validated with the provider.",
        3: "The user story has been completed by the provider with respect to Q/T issues, but still needs to be validated jointly with the customer.",
        4: "All the useful parts of the user story (F/Q/T) are shown, allowing the effort need to size and estimate it, and validated by both parts.",
        5: "The user story quality permits highly objective and low-uncertainty estimation (e.g., suitable for Functional Size Measurement (FSM) reference).",
    },
    "S": {
        1: "The user story is very large and cannot be completed within a Sprint.",
        2: "The user story is very large, but can be completed within a Sprint along with other user story, though it cannot accommodate the creation/delivery of other user story.",
        3: "The user story size is such that it can be completed within a Sprint jointly with other user story, but it is too small to create overhead about the Testing phase.",
        4: "The size of the user story ensures an appropriate balance between development and testing activities within a Sprint.",
        5: "The user story is defined at the level of the elementary process concept (the smallest unit meaningful to the user storyer), maximizing quality and readability.",
    },
    "T": {
        1: "The user story does not include any indication or detail about Acceptance Tests.",
        2: "The user story includes a formal indication of Acceptance Tests, but they are not yet completed or validated.",
        3: "The user story includes Acceptance Tests that are drafted and partially complete, but they still need validation with the customer or provider.",
        4: "The user story includes clearly defined Acceptance Tests which are complete, though not yet validated by both parties.",
        5: "The user story includes completed and validated Acceptance Tests, ensuring clear verification of the requirements.",
    }
}


# === Thresholds (LM Assertion use) ===
def get_invest_rubric_text(dim: str, score: int, scale: str = "1-5") -> str:
    if scale != "1-5":
        return ""
    dim = (dim or "").upper().strip()
    if dim not in INVEST_RUBRIC_15:
        return ""
    step = max(1, min(5, int(round(score))))
    return INVEST_RUBRIC_15[dim][step]

# thresholds & weights on 1–5
INVEST_THRESHOLDS = {d: 3.0 for d in DIM_KEYS}
INVEST_WEIGHTS = {d: 1.0 / len(DIM_KEYS) for d in DIM_KEYS}

INVEST_RUBRIC = INVEST_RUBRIC_15