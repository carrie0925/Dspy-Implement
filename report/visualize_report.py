"""
Visualization helpers for INVEST reports.
Generates simple plots for ΔOverall and mean Δ per INVEST dimension.
"""

from pathlib import Path
import glob
import pandas as pd
import matplotlib.pyplot as plt

DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

def load_latest_csv(report_dir: str = "report"):
    files = sorted(glob.glob(f"{report_dir}/invest_report_*.csv"))
    if not files:
        raise FileNotFoundError("No report CSV found.")
    latest = files[-1]
    df = pd.read_csv(latest)
    return df, latest

def plot_delta_overall_hist(df: pd.DataFrame, out_path: str = "report/plot_delta_overall_hist.png"):
    s = pd.to_numeric(df.get("delta_overall", []), errors="coerce").dropna()
    plt.figure()
    s.plot(kind="hist", bins=10, title="ΔOverall (latest run)")
    plt.xlabel("ΔOverall"); plt.ylabel("Count")
    plt.tight_layout(); plt.savefig(out_path); plt.close()
    return out_path

def plot_dim_delta_bars(df: pd.DataFrame, out_path: str = "report/plot_delta_dims_bar.png"):
    means, labels = [], []
    for d in DIM_KEYS:
        col = f"delta_{d}"
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            labels.append(d); means.append(vals.mean() if not vals.empty else 0.0)
    plt.figure()
    plt.bar(labels, means)
    plt.title("Mean Δ per INVEST dimension (latest run)")
    plt.xlabel("Dimension"); plt.ylabel("Mean Δ")
    plt.tight_layout(); plt.savefig(out_path); plt.close()
    return out_path

# --- Optional: compare two CSVs on mean ΔOverall (for baseline vs DSPy) ---

def mean_delta_overall(df: pd.DataFrame) -> float:
    if "delta_overall" not in df.columns:
        return 0.0
    s = pd.to_numeric(df["delta_overall"], errors="coerce").dropna()
    return float(s.mean()) if not s.empty else 0.0

def compare_two_runs(csv_a: str, csv_b: str, out_path: str = "report/compare_mean_delta_overall.png"):
    A = pd.read_csv(csv_a)
    B = pd.read_csv(csv_b)
    mA = mean_delta_overall(A)
    mB = mean_delta_overall(B)

    plt.figure()
    plt.bar(["Run A", "Run B"], [mA, mB])
    plt.title("Mean ΔOverall: Run A vs Run B")
    plt.ylabel("Mean ΔOverall")
    for i, v in enumerate([mA, mB]):
        plt.text(i, v, f"{v:+.3f}", ha="center", va="bottom")
    plt.tight_layout(); plt.savefig(out_path); plt.close()
    return out_path
