"""
LM Assertion Rules for INVEST
--------------------------------------
- Threshold check against INVEST (0~3 scale by default)
- Weighted overall computation
- Suggest messages per low dimension
- Safe rescaling 0~3 <-> 1~5 for interoperability

Depends on: core/invest_rules.py
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .invest_rules import (
    INVEST_RUBRIC,
    INVEST_THRESHOLDS,
    INVEST_WEIGHTS,
)

# -----------------------------
# Scale utilities
# -----------------------------

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def rescale_03_to_15(x: float) -> float:
    """Map 0~3 → 1~5 (linear)."""
    return clamp(1.0 + (x * 4.0 / 3.0), 1.0, 5.0)

def rescale_15_to_03(x: float) -> float:
    """Map 1~5 → 0~3 (linear)."""
    return clamp((x - 1.0) * 3.0 / 4.0, 0.0, 3.0)

# -----------------------------
# Overall computation
# -----------------------------

DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

def compute_overall_03(scores_03: Dict[str, float]) -> float:
    """
    Compute weighted overall on 0~3 scale using INVEST_WEIGHTS.
    Expects keys I,N,V,E,S,T on 0~3 scale.
    """
    num = 0.0
    den = 0.0
    for k in DIM_KEYS:
        w = float(INVEST_WEIGHTS.get(k, 1.0))
        num += w * float(scores_03.get(k, 0.0))
        den += w
    return 0.0 if den == 0 else num / den

def ensure_overall(scores: Dict[str, float], scale: str = "0-3") -> Dict[str, float]:
    """
    Ensure 'overall' exists; if missing, compute it with weights.
    `scale` indicates the incoming score scale.
    """
    d = dict(scores)
    if "overall" not in d:
        if scale == "0-3":
            d["overall"] = compute_overall_03(d)
        elif scale == "1-5":
            # Convert to 0~3 → compute → back to 1~5
            tmp = {k: rescale_15_to_03(d.get(k, 1.0)) for k in DIM_KEYS}
            d["overall"] = rescale_03_to_15(compute_overall_03(tmp))
        else:
            raise ValueError("scale must be '0-3' or '1-5'")
    return d

# -----------------------------
# Suggest rules (human-written)
# -----------------------------

SUGGEST_RULES: Dict[str, str] = {
    "I": "Make the story self-contained: remove cross-story dependencies or state clear prerequisites.",
    "N": "Avoid prescribing implementation details; describe goals/constraints to keep room for negotiation.",
    "V": "Clarify user/business value (use a concrete 'so that ...' clause and beneficiary).",
    "E": "Narrow scope and list assumptions/boundaries so effort can be estimated.",
    "S": "Split into smaller, deliverable slices that fit within 1~3 workdays.",
    "T": "Add measurable acceptance criteria (steps, inputs, expected outcomes).",
    "overall": "Improve clarity, completeness, and testability to raise the overall score.",
}

def build_suggest_text(low_dims: List[str]) -> str:
    if not low_dims:
        return ""
    parts = []
    for k in low_dims:
        msg = SUGGEST_RULES.get(k, "").strip()
        if msg:
            parts.append(f"[{k}] {msg}")
    return " ".join(parts)

# -----------------------------
# Threshold checking
# -----------------------------

@dataclass
class AssertionResult:
    passed: bool
    low_dims: List[str]          # which dimensions are below threshold (excluding overall)
    message: str                 # concatenated suggestion (for LLM Rewrite hint)
    details: Dict[str, Tuple[float, float]]  # dim -> (score, threshold) on same scale
    scale: str                   # '0-3' or '1-5'

def _to_03_if_needed(scores: Dict[str, float], scale: str) -> Dict[str, float]:
    if scale == "0-3":
        return scores
    elif scale == "1-5":
        return {k: (rescale_15_to_03(v) if isinstance(v, (int, float)) else v)
                for k, v in scores.items()}
    else:
        raise ValueError("scale must be '0-3' or '1-5'")

def check_thresholds(
    scores: Dict[str, float],
    thresholds: Dict[str, float] = INVEST_THRESHOLDS,
    scale: str = "0-3"
) -> AssertionResult:
    """
    Validate scores against thresholds.
    Inputs can be in 0~3 or 1~5 scale (select via `scale`).
    Returns an AssertionResult; `details` always reported on 0~3 scale for consistency.
    """
    # normalize to 0~3 scale for comparison
    s03 = _to_03_if_needed(ensure_overall(scores, scale=scale), scale=scale)

    details: Dict[str, Tuple[float, float]] = {}
    low_dims: List[str] = []

    # check each threshold (including overall)
    for k, thr in thresholds.items():
        val = float(s03.get(k, 0.0))
        details[k] = (val, float(thr))
        if val < float(thr):
            if k != "overall":  # we collect only per-dimension deficits here
                low_dims.append(k)

    passed = all(details[k][0] >= details[k][1] for k in thresholds.keys())
    # build suggestion text (include overall advice if overall failed)
    suggest_keys = list(low_dims)
    if details.get("overall", (0.0, 0.0))[0] < details.get("overall", (0.0, 0.0))[1]:
        suggest_keys = ["overall"] + suggest_keys
    message = build_suggest_text(suggest_keys)

    return AssertionResult(
        passed=passed,
        low_dims=low_dims,
        message=message,
        details=details,
        scale="0-3",
    )

# -----------------------------
# Convenience helpers for pipelines
# -----------------------------

def dims_below_threshold(scores: Dict[str, float], scale: str = "0-3") -> List[str]:
    """Return dimension keys that are below threshold (excludes 'overall')."""
    return check_thresholds(scores, scale=scale).low_dims

def need_refine(scores: Dict[str, float], scale: str = "0-3") -> bool:
    """Return True if any dimension or overall is below threshold."""
    ar = check_thresholds(scores, scale=scale)
    return not ar.passed

def summarize_assertion(ar: AssertionResult) -> str:
    """
    Human-readable summary; useful for logs or as Rewrite guidance.
    """
    lines = []
    lines.append(f"[Assertion] passed={ar.passed} (scale={ar.scale})")
    for k in ["overall"] + DIM_KEYS:
        if k in ar.details:
            v, thr = ar.details[k]
            status = "OK" if v >= thr else "LOW"
            lines.append(f" - {k}: {v:.2f} / {thr:.2f}  ({status})")
    if ar.message:
        lines.append(f"[Suggest] {ar.message}")
    return "\n".join(lines)
