"""
Few-Shot Examples for INVEST Evaluation
--------------------------------------
This module provides annotated User Story examples for BootstrapFewShot training.
Used by: pipeline.py (BootstrapFewShot)
"""

import json
from dspy import Example

# -----------------------------
# Good examples 
# -----------------------------
GOOD_EXAMPLES = [
    Example(
        input_text=(
            "As a user, I want to reset my password via email so that I can regain access if I forget it. "
            "Acceptance Criteria: User requests reset link, receives email, and successfully resets password."
        ),
        result_json=json.dumps({
            "overall": 3,
            "I": 3, "N": 3, "V": 3, "E": 3, "S": 3, "T": 3,
            "reasons": {
                "I": "Self-contained; no dependency on other stories.",
                "N": "Goal-oriented description allows discussion of implementation.",
                "V": "Clear end-user value in regaining account access.",
                "E": "Effort easily estimated; common flow.",
                "S": "Small scope; one feature.",
                "T": "Includes clear testable acceptance criteria."
            }
        })
    ),
    Example(
        input_text=(
            "As an admin, I want to export user data to CSV so that I can perform offline analysis. "
            "Acceptance Criteria: Button 'Export to CSV' exports all active user records with accurate fields."
        ),
        result_json=json.dumps({
            "overall": 3,
            "I": 3, "N": 3, "V": 3, "E": 3, "S": 3, "T": 3,
            "reasons": {
                "I": "Fully independent export function.",
                "N": "Defines output and scope without enforcing technology.",
                "V": "Clear business value for data analysis.",
                "E": "Scope predictable; effort estimable.",
                "S": "Single operation, small feature.",
                "T": "Has precise acceptance condition."
            }
        })
    )
]

# -----------------------------
# Poor examples 
# -----------------------------
BAD_EXAMPLES = [
    Example(
        input_text=(
            "Improve dashboard performance."
        ),
        result_json=json.dumps({
            "overall": 1,
            "I": 2, "N": 1, "V": 1, "E": 1, "S": 1, "T": 0,
            "reasons": {
                "I": "Too vague; may depend on multiple modules.",
                "N": "No room for negotiation; lacks goal context.",
                "V": "Does not express user or business value.",
                "E": "No scope or estimation possible.",
                "S": "Not a deliverable story.",
                "T": "No acceptance test defined."
            }
        })
    ),
    Example(
        input_text=(
            "Add OAuth2 authentication with JWT tokens and integrate with Redis cache layer for session tracking."
        ),
        result_json=json.dumps({
            "overall": 1,
            "I": 2, "N": 0, "V": 1, "E": 1, "S": 1, "T": 1,
            "reasons": {
                "I": "Depends on multiple systems (Redis, JWT).",
                "N": "Written as a technical specification; no discussion space.",
                "V": "No user benefit; purely implementation.",
                "E": "Too complex for estimation.",
                "S": "Too large for one sprint.",
                "T": "No clear validation steps."
            }
        })
    )
]

# -----------------------------
# Aggregate dataset
# -----------------------------
INVEST_FEWSHOTS = GOOD_EXAMPLES + BAD_EXAMPLES

def make_fewshot_dataset(k: int = 4):
    """
    Return first k examples for teleprompter training.
    """
    return INVEST_FEWSHOTS[:k]
