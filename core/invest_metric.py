# -*- coding: utf-8 -*-
"""
invest_metric.py — Native 1–5 scale version
-------------------------------------------

Purpose
-------
- Provide utilities to compute INVEST metrics on a 1–5 scale.
- Used by pipeline.py to evaluate each User Story and output CSV reports.
- This replaces the old 0–3 scale logic (no rescaling anymore).

Author: YOU
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field

# Import shared definitions
from .invest_rules import DIM_KEYS, INVEST_THRESHOLDS, INVEST_WEIGHTS
from .assertion_rules import compute_overall_15, assert_invest


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
SCALE: str = "1-5"
LO, HI = 1.0, 5.0


# ---------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------
@dataclass
class InvestScore:
    """Container for one User Story's INVEST evaluation result."""
    story_id: str
    scores: Dict[str, float]
    overall: float
    passed: bool
    low_dims: List[str] = field(default_factory=list)
    message: str = ""


# ---------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------
def clamp_15(x: float) -> float:
    """Clamp score between 1 and 5."""
    return max(LO, min(HI, float(x)))


def normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """Ensure scores contain all INVEST dimensions and are in range [1,5]."""
    fixed = {}
    for d in DIM_KEYS:
        v = scores.get(d, 3.0)
        fixed[d] = clamp_15(v)
    return fixed


def compute_invest_score(
    story_id: str,
    scores15: Dict[str, float],
    *,
    thresholds: Optional[Dict[str, float]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> InvestScore:
    """
    Compute INVEST evaluation for a single User Story (1–5 scale).

    Parameters
    ----------
    story_id : str
        Identifier for the user story.
    scores15 : dict
        Raw dimension scores (I, N, V, E, S, T) on 1–5 scale.
    thresholds : dict, optional
        Custom per-dimension thresholds (default from invest_rules).
    weights : dict, optional
        Custom weights (default from invest_rules).

    Returns
    -------
    InvestScore
    """
    scores = normalize_scores(scores15)
    result = assert_invest(scores, thresholds=thresholds or INVEST_THRESHOLDS, weights=weights or INVEST_WEIGHTS)

    return InvestScore(
        story_id=story_id,
        scores=scores,
        overall=result.overall,
        passed=result.passed,
        low_dims=result.low_dims,
        message=result.message,
    )


def batch_compute_invest(
    data: List[Dict[str, float]],
    *,
    thresholds: Optional[Dict[str, float]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> List[InvestScore]:
    """
    Compute INVEST scores for a batch of User Stories.

    Parameters
    ----------
    data : list of dict
        Each dict must contain {"id": str, "I":..., "N":..., "V":..., "E":..., "S":..., "T":...}.
    thresholds : dict, optional
        Per-dimension thresholds (default INVEST_THRESHOLDS).
    weights : dict, optional
        Per-dimension weights (default INVEST_WEIGHTS).

    Returns
    -------
    list of InvestScore
    """
    results: List[InvestScore] = []
    for item in data:
        story_id = str(item.get("id") or item.get("story_id") or f"US_{len(results)+1}")
        scores = {d: item.get(d, 3.0) for d in DIM_KEYS}
        result = compute_invest_score(story_id, scores, thresholds=thresholds, weights=weights)
        results.append(result)
    return results


# ---------------------------------------------------------------------
# Optional: CSV Export Helper
# ---------------------------------------------------------------------
def invest_scores_to_rows(results: List[InvestScore]) -> List[Dict[str, float]]:
    """
    Convert list of InvestScore objects to plain dicts for CSV writing.

    Each dict contains: id, I..T, overall, passed, low_dims, message.
    """
    rows = []
    for r in results:
        row = {"id": r.story_id, "overall": round(r.overall, 2), "passed": r.passed}
        for d in DIM_KEYS:
            row[d] = round(r.scores.get(d, 3.0), 2)
        row["low_dims"] = ",".join(r.low_dims)
        row["message"] = r.message
        rows.append(row)
    return rows


# ---------------------------------------------------------------------
# Example Usage (for testing)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    sample_data = [
        {"id": "US_001", "I": 4, "N": 3, "V": 5, "E": 4, "S": 3, "T": 4},
        {"id": "US_002", "I": 2, "N": 2, "V": 3, "E": 2, "S": 3, "T": 2},
    ]
    results = batch_compute_invest(sample_data)
    for r in results:
        print(f"{r.story_id} | Overall={r.overall:.2f} | Passed={r.passed}")
        print(r.message)
        print("-" * 80)
