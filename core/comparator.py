"""
Comparator for INVEST Evaluation Results
----------------------------------------
Compute delta scores between before / after optimization.
Used after pipeline optimization to analyze improvement.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

def _pick_metrics_container(r: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Find the list that holds evaluation metrics across rounds.
    Accepts keys: 'history', 'metrics_history', 'evals', 'rounds', 'evaluations'
    Each element can be:
      - {"text": "...", "metrics": {...}}
      - {"metrics": {...}}
      - {...}  # metrics dict directly
    """
    for key in ["history", "metrics_history", "evals", "rounds", "evaluations"]:
        val = r.get(key)
        if isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
            return val
    return None

def _unwrap_metrics(x: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(x, dict):
        return {}
    return x.get("metrics", x)

def _first_last_metrics(r: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    hist = _pick_metrics_container(r)
    if not hist:
        return {}, {}
    return _unwrap_metrics(hist[0]) or {}, _unwrap_metrics(hist[-1]) or {}

def _scores_of(m: Dict[str, Any]) -> Dict[str, Any]:
    out = {"overall": m.get("overall")}
    for k in DIM_KEYS:
        out[k] = m.get(k)
    return out

def aggregate_results(results: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for idx, r in enumerate(results):
        rid    = r.get("id", idx)
        status = r.get("status", "done")
        rounds = r.get("rounds", 0)
        ftext  = r.get("final_text", "")

        first_m, last_m = _first_last_metrics(r)
        first = _scores_of(first_m) if first_m else {k: None for k in ["overall", *DIM_KEYS]}
        last  = _scores_of(last_m)  if last_m  else {k: None for k in ["overall", *DIM_KEYS]}

        row = {
            "id": rid,
            "status": status,
            "rounds": rounds,
            "overall_before": first["overall"],
            "overall_after":  last["overall"],
            "final_text": ftext,
        }

        for k in DIM_KEYS:
            row[f"{k}_before"] = first.get(k)
            row[f"{k}_after"]  = last.get(k)
            a, b = first.get(k), last.get(k)
            row[f"delta_{k}"]  = (float(b) - float(a)) if (a is not None and b is not None) else None

        a, b = first.get("overall"), last.get("overall")
        row["delta_overall"] = (float(b) - float(a)) if (a is not None and b is not None) else None

        rows.append(row)

    return pd.DataFrame.from_records(rows)
