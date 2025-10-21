"""
Comparator for INVEST Evaluation Results
----------------------------------------
Compute before/after scores and deltas. 
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

def _pick_hist(r: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    for key in ["history", "metrics_history", "evals", "rounds", "evaluations"]:
        val = r.get(key)
        if isinstance(val, list) and val and all(isinstance(x, dict) for x in val):
            return val
    return None

def _unwrap_metrics(x: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(x, dict): return {}
    return x.get("metrics", x)

def _first_last_metrics(r: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    h = _pick_hist(r)
    if not h: return {}, {}
    return _unwrap_metrics(h[0]) or {}, _unwrap_metrics(h[-1]) or {}

def _scores(m: Dict[str, Any]) -> Dict[str, Any]:
    out = {"overall": m.get("overall")}
    for k in DIM_KEYS: out[k] = m.get(k)
    return out

def _first_text(r: Dict[str, Any]) -> str:
    h = _pick_hist(r)
    if h and isinstance(h[0].get("text"), str):
        return h[0]["text"]
    return r.get("original_text", "")

def aggregate_results(results: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for idx, r in enumerate(results):
        rid    = r.get("id", idx)
        status = r.get("status", "done")
        rounds = r.get("rounds", 0)
        ftext  = r.get("final_text", "")
        otext  = _first_text(r)

        first_m, last_m = _first_last_metrics(r)
        first = _scores(first_m) if first_m else {k: None for k in ["overall", *DIM_KEYS]}
        last  = _scores(last_m)  if last_m  else {k: None for k in ["overall", *DIM_KEYS]}

        row = {
            "id": rid,
            "status": status,
            "rounds": rounds,
            "original_text": otext,  
            "final_text": ftext,
            "overall_before": first["overall"],
            "overall_after":  last["overall"],
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
