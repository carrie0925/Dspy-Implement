"""
INVEST Metric Parser & Validator
--------------------------------------
Purpose:
- Parse and validate LLM JSON output from InvestScoreSig
- Guarantee numeric range consistency (0~3 or 1~5)
- Auto-fill missing keys / clamp invalid values
- Provide safe conversion functions (0~3 <-> 1~5)
"""

import json
from typing import Dict, Any
from dataclasses import dataclass, field
from .assertion_rules import (
    rescale_03_to_15,
    rescale_15_to_03,
    compute_overall_03,
    DIM_KEYS
)

# -----------------------------
# Configurable defaults
# -----------------------------

DEFAULT_SCALE = "0-3"  # could be "1-5" if you want 5-point view
DEFAULT_MINMAX = {
    "0-3": (0, 3),
    "1-5": (1, 5)
}

# -----------------------------
# Data structure
# -----------------------------

@dataclass
class InvestMetric:
    overall: float = 0.0
    I: float = 0.0
    N: float = 0.0
    V: float = 0.0
    E: float = 0.0
    S: float = 0.0
    T: float = 0.0
    reasons: Dict[str, str] = field(default_factory=dict)
    scale: str = DEFAULT_SCALE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "I": self.I, "N": self.N, "V": self.V,
            "E": self.E, "S": self.S, "T": self.T,
            "reasons": self.reasons,
            "scale": self.scale
        }

# -----------------------------
# Core utilities
# -----------------------------

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _parse_json_safe(raw: str) -> Dict[str, Any]:
    """
    Parse raw JSON string safely, stripping unwanted characters.
    """
    try:
        cleaned = raw.strip().strip("```").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"[WARN] JSON parsing failed: {e}")
        return {}

def _ensure_reasons(keys: list, reasons_dict: Dict[str, str]) -> Dict[str, str]:
    """
    Ensure all keys exist in reasons.
    """
    reasons = dict(reasons_dict or {})
    for k in keys:
        reasons.setdefault(k, "")
    return reasons

# -----------------------------
# Public interface
# -----------------------------

def parse_invest_json(raw: str, scale: str = DEFAULT_SCALE) -> InvestMetric:
    """
    Parse LLM output JSON into InvestMetric object.
    Auto-correct invalid/missing values.
    """
    data = _parse_json_safe(raw)
    lo, hi = DEFAULT_MINMAX[scale]
    values = {}

    # Extract scores
    for k in ["overall"] + DIM_KEYS:
        try:
            values[k] = float(data.get(k, 0))
        except Exception:
            values[k] = 0.0
        # Clamp values
        values[k] = clamp(values[k], lo, hi)

    # Fix missing overall (recompute if needed)
    if values["overall"] == 0:
        if scale == "0-3":
            values["overall"] = compute_overall_03(values)
        else:
            tmp03 = {k: rescale_15_to_03(values[k]) for k in DIM_KEYS}
            values["overall"] = rescale_03_to_15(compute_overall_03(tmp03))

    # Extract reasons
    reasons = _ensure_reasons(DIM_KEYS, data.get("reasons", {}))

    return InvestMetric(
        overall=values["overall"],
        I=values["I"], N=values["N"], V=values["V"],
        E=values["E"], S=values["S"], T=values["T"],
        reasons=reasons,
        scale=scale
    )

# -----------------------------
# Conversion helpers
# -----------------------------

def convert_metric_scale(metric: InvestMetric, to_scale: str = "1-5") -> InvestMetric:
    """
    Convert entire metric object between 0~3 and 1~5 scales.
    """
    if metric.scale == to_scale:
        return metric

    if to_scale == "1-5":
        f = rescale_03_to_15
    elif to_scale == "0-3":
        f = rescale_15_to_03
    else:
        raise ValueError("to_scale must be '0-3' or '1-5'")

    new_vals = {k: f(getattr(metric, k)) for k in DIM_KEYS + ["overall"]}
    return InvestMetric(
        overall=new_vals["overall"],
        I=new_vals["I"], N=new_vals["N"], V=new_vals["V"],
        E=new_vals["E"], S=new_vals["S"], T=new_vals["T"],
        reasons=metric.reasons,
        scale=to_scale
    )
