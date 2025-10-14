"""
Main entry for DSPy-based User Story Optimization (INVEST)
No 'title' is required anywhere in the pipeline.
"""

import os
import sys
import json
from pathlib import Path

from core.config_model import configure_lm
configure_lm()

from core.pipeline import run_batch_optimization
from core.report_generator import export_results_csv, summarize_report

def _load_user_stories(data_path: Path):
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of user stories, got: {type(data).__name__}")

    norm = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            item = {"description": str(item)}
        desc = item.get("description") or item.get("text") or item.get("content") or item.get("story")
        if not isinstance(desc, str) or not desc.strip():
            raise ValueError(f"[Index {i}] missing 'description' in: {item}")
        rid = item.get("id", i)
        norm.append({"id": rid, "description": desc})
    return norm

def main():
    default_path = Path("data/user_stories_sample.json")
    arg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    env_path = Path(os.getenv("USER_STORIES_JSON", "")) if os.getenv("USER_STORIES_JSON") else None
    data_path = env_path or arg_path or default_path

    print("=== Step 1: Load user stories ===")
    stories = _load_user_stories(data_path)
    print(f"Loaded {len(stories)} user stories from: {data_path}\n")

    max_rounds = int(os.getenv("INVEST_MAX_ROUNDS", "3"))
    fewshot_k  = int(os.getenv("INVEST_FEWSHOT_K", "4"))
    use_dspy   = os.getenv("USE_DSPY", "1") == "1"

    print("=== Step 2: Start optimization ===")
    print(f"(config) max_rounds={max_rounds}, fewshot_k={fewshot_k}, use_dspy={use_dspy}")

    optimized_results = run_batch_optimization(
        stories,
        max_rounds=max_rounds,
        fewshot_k=fewshot_k,
        use_dspy=use_dspy
    )

    print("=== Step 3: Exporting report ===")
    df = export_results_csv(optimized_results)

    print("=== Step 4: Summary ===")
    summarize_report(df)

    print("\nAll done ✅")

if __name__ == "__main__":
    main()
    # 視覺化（放在 main() 之後，確保 CSV 已產生）
    try:
        from report.visualize_report import load_latest_csv, plot_delta_overall_hist, plot_dim_delta_bars
        df_latest, fpath = load_latest_csv("report")
        print(f"(viz) using latest CSV: {fpath}")
        p1 = plot_delta_overall_hist(df_latest)
        p2 = plot_dim_delta_bars(df_latest)
        print(f"(viz) saved: {p1}, {p2}")
    except Exception as e:
        print("(viz) skip visualization:", e)
