"""
DSPy Signatures for INVEST Evaluation & Rewrite (safe schema version)
---------------------------------------------------------------------
This version defines minimal valid schema-only Signatures.
Rubric text is stored separately in RUBRIC_TEXT.
"""

from typing import Dict, List
import dspy
from .invest_rules import INVEST_RUBRIC


# -------------------------
# Build human-readable rubric text
# -------------------------
def _format_scale_lines(scale: Dict[int, str]) -> str:
    lines = []
    for k in [0, 1, 2, 3]:
        if k in scale:
            lines.append(f"- {k}: {scale[k]}")
    return "\n".join(lines)


def build_invest_rubric_text() -> str:
    parts: List[str] = []
    for key in ["I", "N", "V", "E", "S", "T"]:
        item = INVEST_RUBRIC[key]
        header = f"{key} - {item['name']}: {item['description']}"
        scale = _format_scale_lines(item["scale"])
        parts.append(f"{header}\n{scale}")
    return "\n\n".join(parts)


RUBRIC_TEXT = build_invest_rubric_text()


# -------------------------
# Define minimal Signatures (schema only)
# -------------------------

# Evaluate signature
InvestScoreSig = dspy.Signature("input_text: str, rubric_text: str -> result_json: str")

# Rewrite signature
InvestRewriteSig = dspy.Signature("input_text: str, low_dims_csv: str, suggestions_text: str -> result_json: str")
