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
    {
        "input_text": "As a trainer, I want to list my upcoming classes in my profile and include a link to a detailed page about each, so that prospective attendees can find my courses quickly.",
        "scores": {
            "overall": 3,
            "I": 3, "N": 4, "V": 3, "E": 3, "S": 3, "T": 3,
            "reasons": {
                "overall": "Valuable, but combines listing + linking behavior; somewhat solution-shaped."
            }
        }
    },
    {
        "input_text": "As a site admin, I want to stop publishing jobs on the site 30 days after being posted, so that jobs that may have been filled aren't still listed.",
        "scores": {
            "overall": 4,
            "I": 4, "N": 4, "V": 5, "E": 5, "S": 4, "T": 4,
            "reasons": {
                "overall": "The best story; bounded, estimable, and objectively testable."
            }
        }
    },
    {
        "input_text": "As a site editor, I want to set the following dates on a news item: Start Publishing Date, Old News Date, Stop Publishing Date, so that articles are published on and through appropriate dates.",
        "scores": {
            "overall": 3,
            "I": 3, "N": 4, "V": 4, "E": 3, "S": 3, "T": 3,
            "reasons": {
                "overall": "Good scope framing, but publishing logic is still incomplete and not fully testable from text alone"
            }
        }
    }
]

# -----------------------------
# Poor examples 
# -----------------------------
BAD_EXAMPLES = [
    {
        "input_text": "Improve dashboard performance.",
        "scores": {
            "overall": 2,
            "I": 2, "N": 3, "V": 1, "E": 2, "S": 3, "T": 4,
            "reasons": {
                "overall": "As a site visitor, I want to see new content... (Benefit is circular)"
            }
        }
    },
    {
        "input_text": "As a site visitor, I want to have articles that interest me and are easy to get to, so that I come to the site for my agile news.",
        "scores": {
            "overall": 1,
            "I": 1, "N": 3, "V": 1, "E": 1, "S": 3, "T": 4,
            "reasons": {
                "overall": "Very vague and highly subjective, not a workable story"
            }
        }
    },

    {
        "input_text": "As a trainer, I want to load an Excel file into the site, so that the course participants are added to the Scrum Alliance records.",
        "scores": {
            "overall": 2,
            "I": 3, "N": 2, "V": 2, "E": 3, "S": 3, "T": 2,
            "reasons": {
                "overall": "Concrete action, but benefit is really system completion, not user value; also solution-constrained by “Excel file”"
            }
        }
    }
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
