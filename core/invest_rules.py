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
    "2": "The story can be technically started, but its functional logic relies heavily on the implementation details of another story.",
    "3": "The story is functionally distinct but part of a strict workflow sequence. It requires data or state from a previous step but isn't code-dependent.",
    "4": "The story allows for parallel development. Dependencies are minimized to standard interface agreements (APIs) rather than functional blocks.",
    "5": "The story is fully self-contained, it can be developed and released independently, with no blocking dependencies or required sequencing."
  },
  
  "N": {
    "1": "The story dictates specific technical implementations (e.g., SQL queries, database fields, specific algorithms), leaving no room for alternative solutions.",
    "2": "The story restricts the solution to specific UI elements or interaction details instead of focusing on user goal or intent.",
    "3": "The story states a preferred solution approach. It focuses on 'how' the system behaves rather than 'what' the user needs.",
    "4": "The story clearly states the user's goal and rationale. Technical implementation is open, while only necessary constraints (e.g., policy, compliance or business rules)",
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
    "1": "The story is not sufficiently clear in key action, scope or assumptions, making relative effort estimation for team. (e.g., “Improve performance in some way.”)",
    "2": "The story is partially clear but described in vague terms, resulting in uncertainty. (e.g., “Make the process faster and more user-friendly.”)",
    "3": "The main goal is clear, but important constraints and scope boundaries are not described. (e.g., Allow users to export reports,” without specifying format, limits, or conditions)",
    "4": "The action is concrete, allowing the team to make a reasonable relative effort estimate. Boundaries are inferred clearly from context. (e.g., ”mark as favorite to save items“)",
    "5": "The requirement is clear and tightly scoped, allowing the effort to be estimated with confident relative effort estimation within the team experience."
  },
  
  "S": {
    "1": "Covers an entire module or workflow. Impossible to complete in a single iteration (Sprint). Needs major breakdown.",
    "2": "Contains multiple distinct user goals or verbs (e.g., 'Search AND View AND Edit').",
    "3": "A single user goal but involves complex logic or multiple variations (e.g., the story is likely to exceed sprint capacity.).",
    "4": "A single user goal with a strictly limited scope/scenario (e.g., 'Search by Name only').",
    "5": "The smallest possible slice of functionality that still provides value. Extremely low risk and quick to deliver."
  },
  
  "T": {
    "1": "Criteria depend on subjective judgment (“nice,” “easy,” “appealing”), rather than objective data.",
    "2": "Expected behavior is implied in the description but not explicitly listed as acceptance criteria.",
    "3": "Describes visible system behaviors (like View or Search) but modifies them with vague adverbs (e.g., ”search quickly“, ”find easily“) that prevent definitive pass/fail.",
    "4": "Covers both success and failure scenarios clearly. Testers know exactly what to check. (e.g., “Mark email as private so that no one can contact me”)",
    "5": "Logic is rule-based, involving hard numbers, dates, or state changes, allowing pass/fail outcomes to be verified through testing(e.g., Limited posting time)"
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