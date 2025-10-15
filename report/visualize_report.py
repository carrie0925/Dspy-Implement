"""
Visualization helpers for INVEST reports (per-run folder aware).
"""

import os, glob
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DIM_KEYS = ["I","N","V","E","S","T"]

def load_latest_csv(run_dir: str):
    files = sorted(glob.glob(os.path.join(run_dir, "invest_report_*.csv")))
    if not files: raise FileNotFoundError(f"No report CSV found in {run_dir}.")
    latest = files[-1]
    return pd.read_csv(latest), latest

def plot_delta_overall_hist(df: pd.DataFrame, run_dir: str) -> str:
    out_path = os.path.join(run_dir, "plot_delta_overall_hist.png")
    s = pd.to_numeric(df.get("delta_overall", []), errors="coerce").dropna()
    plt.figure()
    s.plot(kind="hist", bins=10, title="ΔOverall (this run)")
    plt.xlabel("ΔOverall"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(out_path); plt.close()
    return out_path

def plot_dim_delta_bars(df: pd.DataFrame, run_dir: str) -> str:
    out_path = os.path.join(run_dir, "plot_delta_dims_bar.png")
    means, labels = [], []
    for d in DIM_KEYS:
        col = f"delta_{d}"
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            labels.append(d); means.append(vals.mean() if not vals.empty else 0.0)
    plt.figure()
    plt.bar(labels, means)
    plt.title("Mean Δ per INVEST dimension (this run)")
    plt.xlabel("Dimension"); plt.ylabel("Mean Δ")
    plt.tight_layout(); plt.savefig(out_path); plt.close()
    return out_path
