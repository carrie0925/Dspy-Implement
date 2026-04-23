# -*- coding: utf-8 -*-
"""

Purpose
-------
- Use 1–5 as the internal & external scale for INVEST evaluation.
- Compute weighted overall score on 1–5.
- Check per-dimension and overall thresholds (1–5).
- Produce human-readable feedback with optional rubric text.

Integration Notes
-----------------
- This module *optionally* uses `get_invest_rubric_text(dim, score, scale="1-5")`
  from `invest_rules.py`. If not available, it gracefully degrades.

Public API
----------
- assert_invest(scores15: dict, *, weights=None, thresholds=None, overall_min=None) -> AssertionResult
- ensure_overall(scores15: dict, *, weights=None) -> dict
- summarize_assertion(result: AssertionResult) -> str

Data Contracts
--------------
- Input scores: dict with keys in {"I","N","V","E","S"}; values in [1, 5].
- Output result: AssertionResult with details & message.

Author: YOU
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# --- Optional rubric import (safe fallback) -----------------------------------
try:
    # You will provide this in invest_rules.py next
    from .invest_rules import get_invest_rubric_text, DIM_KEYS as _DIM_KEYS
except Exception:  # pragma: no cover
    def get_invest_rubric_text(dim: str, score: int, scale: str = "1-5") -> str:
        return ""  # fallback: no rubric text available
    _DIM_KEYS = ["I", "N", "V", "E", "S"]

# --- Constants / Defaults -----------------------------------------------------
SCALE: str = "1-5"
DIM_KEYS: List[str] = list(_DIM_KEYS)

# Equal weights by default (sum to 1.0)
DEFAULT_WEIGHTS: Dict[str, float] = {d: 1.0 / len(DIM_KEYS) for d in DIM_KEYS}

# Per-dimension minimum threshold (1–5). Default 3.0 = "acceptable"
DEFAULT_THRESHOLDS: Dict[str, float] = {d: 3.0 for d in DIM_KEYS}

# Overall minimum threshold on 1–5
DEFAULT_OVERALL_MIN: float = 3.0

# Clamp bounds
LO, HI = 1.0, 5.0


# --- Data classes -------------------------------------------------------------
@dataclass
class AssertionResult:
    passed: bool
    scale: str = SCALE
    overall: float = 0.0
    details: Dict[str, float] = field(default_factory=dict)
    low_dims: List[str] = field(default_factory=list)
    message: str = ""


# --- Utilities ----------------------------------------------------------------
def _clamp01(x: float, lo: float = LO, hi: float = HI) -> float:
    return max(lo, min(hi, float(x)))


def _validate_and_cast_scores(scores15: Dict[str, float]) -> Dict[str, float]:
    """Ensure dict has only DIM_KEYS and values in [1,5]; missing dims are filled with 3.0."""
    out: Dict[str, float] = {}
    for d in DIM_KEYS:
        v = scores15.get(d, 3.0)
        out[d] = _clamp01(v, LO, HI)
    return out


def _normalize_weights(weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    """Return normalized weights over DIM_KEYS."""
    if not weights:
        return dict(DEFAULT_WEIGHTS)
    total = sum(max(0.0, float(weights.get(d, 0.0))) for d in DIM_KEYS)
    if total <= 0.0:
        return dict(DEFAULT_WEIGHTS)
    return {d: max(0.0, float(weights.get(d, 0.0))) / total for d in DIM_KEYS}


def _compose_rubric_hint(dim: str, score: float) -> str:
    """
    Return a short hint derived from rubric text around the nearest integer step.
    If rubric text isn't available, return an empty string.
    """
    step = int(round(_clamp01(score)))
    text = get_invest_rubric_text(dim, step, scale=SCALE)
    if not text:
        return ""
    # Keep it concise (you can tailor truncation if needed)
    return f"Guideline ({dim}={step}): {text}"


# --- Core computations ---------------------------------------------------------
def compute_overall_15(scores15: Dict[str, float], *, weights: Optional[Dict[str, float]] = None) -> float:
    """Weighted average on 1–5 scale."""
    s = _validate_and_cast_scores(scores15)
    w = _normalize_weights(weights)
    return sum(s[d] * w[d] for d in DIM_KEYS)


def ensure_overall(scores15: Dict[str, float], *, weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """Return a copy with 'overall' field (1–5)."""
    out = dict(_validate_and_cast_scores(scores15))
    out["overall"] = compute_overall_15(out, weights=weights)
    out["_internal_scale"] = SCALE
    out["_external_scale"] = SCALE
    return out


def _check_thresholds(
    scores15: Dict[str, float],
    *,
    thresholds: Optional[Dict[str, float]] = None,
    overall_min: Optional[float] = None
) -> Tuple[bool, List[str], float]:
    """Check per-dimension thresholds and overall threshold. Returns (passed, low_dims, overall)."""
    s = _validate_and_cast_scores(scores15)
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        for d in DIM_KEYS:
            if d in thresholds:
                th[d] = _clamp01(thresholds[d])

    o_min = _clamp01(overall_min if overall_min is not None else DEFAULT_OVERALL_MIN)
    overall = compute_overall_15(s)

    low_dims = [d for d in DIM_KEYS if s[d] < th[d]]
    passed = (len(low_dims) == 0) and (overall >= o_min)
    return passed, low_dims, overall


def _build_feedback_message(
    scores15: Dict[str, float],
    *,
    thresholds: Optional[Dict[str, float]] = None,
    overall_min: Optional[float] = None
) -> str:
    """Produce a compact, actionable feedback message."""
    s = _validate_and_cast_scores(scores15)
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        for d in DIM_KEYS:
            if d in thresholds:
                th[d] = _clamp01(thresholds[d])

    o_min = _clamp01(overall_min if overall_min is not None else DEFAULT_OVERALL_MIN)
    overall = compute_overall_15(s)

    low_dims = [d for d in DIM_KEYS if s[d] < th[d]]

    if not low_dims and overall >= o_min:
        return f"✅ Passed. Overall={overall:.2f} (min {o_min:.2f}). All dimensions meet or exceed thresholds."

    parts: List[str] = []
    if low_dims:
        parts.append("⚠️ Improve these dimensions:")
        for d in low_dims:
            gap = th[d] - s[d]
            hint = _compose_rubric_hint(d, s[d])
            base = f"- {d}: {s[d]:.2f} < {th[d]:.2f} (gap {gap:+.2f})"
            if hint:
                parts.append(f"{base}\n  {hint}")
            else:
                parts.append(base)

    if overall < o_min:
        parts.append(f"ℹ️ Overall={overall:.2f} is below min {o_min:.2f}. Focus on raising low dimensions first.")

    return "\n".join(parts)


# --- Public API ----------------------------------------------------------------
def assert_invest(
    scores15: Dict[str, float],
    *,
    weights: Optional[Dict[str, float]] = None,
    thresholds: Optional[Dict[str, float]] = None,
    overall_min: Optional[float] = None
) -> AssertionResult:
    """
    Main entry to validate INVEST on native 1–5 scale.

    Parameters
    ----------
    scores15 : dict
        {"I": float, "N": float, "V": float, "E": float, "S": float}, each in [1,5].
    weights : dict, optional
        Per-dimension weights (will be normalized). Defaults to equal weights.
    thresholds : dict, optional
        Per-dimension minimum thresholds in [1,5]. Default 3.0.
    overall_min : float, optional
        Overall minimum threshold in [1,5]. Default 3.0.

    Returns
    -------
    AssertionResult
    """
    s = _validate_and_cast_scores(scores15)
    passed, low_dims, overall = _check_thresholds(s, thresholds=thresholds, overall_min=overall_min)
    msg = _build_feedback_message(s, thresholds=thresholds, overall_min=overall_min)

    return AssertionResult(
        passed=passed,
        scale=SCALE,
        overall=overall,
        details=s,
        low_dims=low_dims,
        message=msg,
    )


def summarize_assertion(result: AssertionResult) -> str:
    """Compact single-paragraph summary suitable for logs/UI."""
    status = "PASSED" if result.passed else "FAILED"
    dims = " ".join([f"{d}:{result.details.get(d, 0):.2f}" for d in DIM_KEYS])
    low = ", ".join(result.low_dims) if result.low_dims else "—"
    return f"[{status}] Overall={result.overall:.2f} | {dims} | LowDims={low}"
