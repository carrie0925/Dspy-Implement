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
    "1": "The story is explicitly blocked by or dependent on the completion of other specific stories. It cannot be started until others are finished.",
    "2": "The story can be technically started, but its functional logic relies heavily on the implementation details of another story (e.g., 'similar to story #5').",
    "3": "The story is functionally distinct but part of a strict workflow sequence. It requires data or state from a previous step but isn't code-dependent.",
    "4": "The story allows for parallel development. Dependencies are minimized to standard interface agreements (APIs) rather than functional blocks.",
    "5": "The story can be prioritized, developed, tested, and deployed in any order without any friction or external blockers."
  },
  
  "N": {
    "1": "The story dictates specific technical implementations (e.g., SQL queries, database fields, specific algorithms), leaving no room for discussion.",
    "2": "The story restricts the solution to specific UI elements (e.g., 'click the blue button at top-right') rather than user intent.",
    "3": "The story focuses on 'how' the system behaves rather than 'what' the user needs. The solution is proposed, but details can be tweaked.",
    "4": "The story clearly states the user's goal. Technical implementation is open, though some functional constraints are mentioned.",
    "5": "The story defines a pure business problem or user need. It invites the team to co-create the best solution (UI/Tech) during refinement."
  },
  
  "V": {
    "1": "Describes a developer task (e.g., 'refactor code', 'create table') with no discernible user or business value.",
    "2": "The value statement repeats the feature (e.g., 'I want to login so that I am logged in'). The 'Why' adds no new information.",
    "3": "The value is understandable by context but vague or generic (e.g., 'to save time', 'for better UX') without specific justification.",
    "4": "Clearly articulates a specific benefit to a specific persona (e.g., 'so that I don't lose my work during connection loss').",
    "5": "The value is tied to a measurable business objective or key result (e.g., 'reduce support tickets by 10%', 'increase conversion')."
  },
  
  "E": {
    "1": "Lacks critical information. The team cannot understand what is being asked (e.g., 'make it better'). Estimation is impossible.",
    "2": "Contains subjective terms (e.g., 'fast', 'easy', 'user-friendly') that make the scope elastic and high-risk.",
    "3": "The core requirement is clear, but edge cases, error handling, or non-functional requirements are missing.",
    "4": "Functional and non-functional boundaries are clear. The team can estimate with high confidence, barring minor clarifications.",
    "5": "Fully detailed with no known unknowns. All developers share a consistent understanding of the scope and effort involved."
  },
  
  "S": {
    "1": "Covers an entire module or workflow. Impossible to complete in a single iteration (Sprint). Needs major breakdown.",
    "2": "Contains multiple distinct user goals or verbs (e.g., 'Search AND View AND Edit'). High cognitive load.",
    "3": "A single user goal but involves complex logic or multiple variations (e.g., 'Search with 10 different filters').",
    "4": "A single user goal with a strictly limited scope/scenario (e.g., 'Search by Name only'). Fits comfortably in a sprint.",
    "5": "The smallest possible slice of functionality that still provides value. Extremely low risk and quick to deliver."
  },
  
  "T": {
    "1": "No criteria provided, or criteria are purely subjective (e.g., 'must look modern').",
    "2": "Expected behavior is implied in the description but not explicitly listed as acceptance criteria.",
    "3": "Acceptance criteria exist as a prose list (bullet points) but may lack precision or cover only the 'Happy Path'.",
    "4": "Covers both success and failure scenarios clearly. Testers know exactly what to check.",
    "5": "Criteria are written in a format ready for automation (e.g., Gherkin/Given-When-Then), with quantified metrics and data examples."
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