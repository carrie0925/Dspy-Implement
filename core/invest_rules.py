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
DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

# --- INVEST Rubric (1–5 Scale) ------------------------------------------------
INVEST_RUBRIC_15 = {
  "I": {
    "1": "The user story is strongly dependent on other stories; it cannot be developed or delivered independently.",
    "2": "The user story's independence is unclear or partially constrained by external workflows, preventing standalone development.",
    "3": "The user story is logically separate, but implicit dependencies or sequencing constraints still need clarification.",
    "4": "The user story is explicitly independent with clearly defined boundaries, making it feasible to develop without blocking others.",
    "5": "The user story demonstrates full autonomy with no technical, business, or sequencing dependencies, enabling immediate and flexible deployment."
  },
  "N": {
    "1": "The user story is overly prescriptive or written like a specification, leaving no room for negotiation or refinement.",
    "2": "The user story includes minimal context; scope is partially negotiable but still rigid or ambiguous.",
    "3": "The user story describes a meaningful requirement but requires collaborative refinement to finalize scope.",
    "4": "The user story is well-structured, high-level, and clearly open to feedback and negotiation between stakeholders.",
    "5": "The user story expresses a high-level need with optimal clarity and flexibility, enabling effective negotiation while preventing premature scope lock-in."
  },
  "V": {
    "1": "The user story provides little or no user-visible value; the benefit is vague, generic, or not tied to a real outcome.",
    "2": "The user story states value but it remains fuzzy, qualitative, or non-measurable (e.g., 'so it's easier', 'so I can learn').",
    "3": "The user story delivers a clear qualitative user benefit but lacks measurable impact or business alignment.",
    "4": "The user story conveys strong, identifiable value aligned with user or business goals.",
    "5": "The user story provides explicit, measurable, and outcome-driven value, exceeding functional correctness and clearly supporting a business objective."
  },
  "E": {
    "1": "The user story lacks sufficient clarity or detail to be estimated; major uncertainties prevent meaningful sizing.",
    "2": "The user story is partly understandable and estimation is possible but highly uncertain due to missing boundaries or logic.",
    "3": "The user story contains enough detail for a coarse estimate but still requires clarification to reduce estimation risk.",
    "4": "The user story is well-defined with clearly articulated functional logic, enabling accurate and low-risk estimation.",
    "5": "The user story is fully detailed and unambiguous across functional and non-functional aspects, allowing precise estimation with minimal uncertainty."
  },
  "S": {
    "1": "The user story is too large, broad, or complex to be completed within a single Sprint.",
    "2": "The user story could fit in a Sprint only after significant decomposition or by combining with other tasks.",
    "3": "The user story fits within a Sprint but still includes multiple steps that may introduce overhead.",
    "4": "The user story is appropriately sized to balance development and testing within a Sprint.",
    "5": "The user story represents a minimal, atomic, user-meaningful increment, reflecting the smallest unit of deliverable value."
  },
  "T": {
    "1": "The user story lacks any acceptance criteria or observable outcomes, making verification impossible.",
    "2": "The user story references expected behavior but provides no concrete or actionable acceptance tests.",
    "3": "The user story includes partial or draft acceptance tests that require refinement or stakeholder validation.",
    "4": "The user story contains clear, verifiable acceptance tests that are complete but not yet validated by all parties.",
    "5": "The user story includes fully validated, precise, and unambiguous acceptance tests, ensuring complete verification of requirements."
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