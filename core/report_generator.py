"""
Report Generator for INVEST Optimization Results
------------------------------------------------
Exports results to CSV and prints summary.

Expected columns:
  id, status, rounds,
  overall_before, overall_after, delta_overall,
  I_before ... T_before, I_after ... T_after,
  delta_I ... delta_T, final_text
"""

import os
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd

from .comparator import aggregate_results

DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

def export_results_csv(results: List[Dict[str, Any]], out_dir: str = "report") -> pd.DataFrame:
    df = aggregate_results(results)
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_csv = os.path.join(out_dir, f"invest_report_{ts}.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Report exported: {out_csv}  (rows={len(df)})")
    return df

def summarize_report(df: pd.DataFrame) -> Dict[str, Any]:
    summary = {
        "pass_rate": 0.0,
        "avg_rounds": 0.0,
        "delta_overall_mean": 0.0,
        "delta_dims_mean": {k: 0.0 for k in DIM_KEYS},
    }
    if df.empty:
        print("⚠️ Empty report. Nothing to summarize.")
        return summary

    pass_thresh = 1.0
    passes = pd.to_numeric(df.get("overall_after", 0), errors="coerce").fillna(0) >= pass_thresh
    summary["pass_rate"] = float(passes.mean())

    summary["avg_rounds"] = float(pd.to_numeric(df.get("rounds", 0), errors="coerce").fillna(0).mean())

    if "delta_overall" in df.columns:
        summary["delta_overall_mean"] = float(pd.to_numeric(df["delta_overall"], errors="coerce").dropna().mean()) \
            if not df["delta_overall"].dropna().empty else 0.0

    delta_dims_mean = {}
    for k in DIM_KEYS:
        col = f"delta_{k}"
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            delta_dims_mean[k] = float(vals.mean()) if not vals.empty else 0.0
        else:
            delta_dims_mean[k] = 0.0
    summary["delta_dims_mean"] = delta_dims_mean

    print("\n=== Summary ===")
    print(f"✔️  Pass rate (overall_after ≥ {pass_thresh:.1f}): {summary['pass_rate']:.2%}")
    print(f"🔁 Avg rounds: {summary['avg_rounds']:.2f}")
    print(f"📈 Avg ΔOverall: {summary['delta_overall_mean']:+.3f}")
    print("\nΔ per dimension (avg):")
    for k in DIM_KEYS:
        print(f"  {k}: {delta_dims_mean[k]:+.3f}")

    return summary
