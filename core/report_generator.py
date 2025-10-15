"""
Report Generator for INVEST Optimization Results
Creates a per-run timestamped folder under ./report.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Tuple
import pandas as pd

from .comparator import aggregate_results

DIM_KEYS = ["I","N","V","E","S","T"]

def export_results_csv(results: List[Dict[str, Any]], out_root: str = "report") -> Tuple[pd.DataFrame, str]:
    df = aggregate_results(results)
    os.makedirs(out_root, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(out_root, ts)
    os.makedirs(run_dir, exist_ok=True)
    out_csv = os.path.join(run_dir, f"invest_report_{ts}.csv")
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Report exported: {out_csv}  (rows={len(df)})")
    return df, run_dir

def summarize_report(df: pd.DataFrame) -> Dict[str, Any]:
    summary = {"pass_rate": 0.0, "avg_rounds": 0.0, "delta_overall_mean": 0.0,
               "delta_dims_mean": {k:0.0 for k in DIM_KEYS}}
    if df.empty:
        print("⚠️ Empty report. Nothing to summarize."); return summary

    passes = pd.to_numeric(df.get("overall_after", 0), errors="coerce").fillna(0) >= 1.0
    summary["pass_rate"] = float(passes.mean())
    summary["avg_rounds"] = float(pd.to_numeric(df.get("rounds", 0), errors="coerce").fillna(0).mean())
    if "delta_overall" in df.columns and not df["delta_overall"].dropna().empty:
        summary["delta_overall_mean"] = float(pd.to_numeric(df["delta_overall"], errors="coerce").dropna().mean())
    for k in DIM_KEYS:
        col = f"delta_{k}"
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            summary["delta_dims_mean"][k] = float(vals.mean()) if not vals.empty else 0.0

    print("\n=== Summary ===")
    print(f"✔️  Pass rate (overall_after ≥ 1.0): {summary['pass_rate']:.2%}")
    print(f"🔁 Avg rounds: {summary['avg_rounds']:.2f}")
    print(f"📈 Avg ΔOverall: {summary['delta_overall_mean']:+.3f}")
    print("\nΔ per dimension (avg):")
    for k,v in summary["delta_dims_mean"].items():
        print(f"  {k}: {v:+.3f}")
    return summary
