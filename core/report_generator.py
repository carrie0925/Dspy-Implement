"""
Report Generator for INVEST Optimization Results (wide table)
Each row = one user story. INVEST/Overall before/after/delta are separate columns.
Creates a per-run timestamped folder under ./report.
"""

import os, re, importlib.util
from datetime import datetime
from typing import Dict, Any, List, Tuple
import pandas as pd

from .comparator import aggregate_results

# ==== load fuzzy terms (separate file) ====
def _load_fuzzy_terms():
    try:
        from .fuzzy_terms import FUZZY_TERMS
        return FUZZY_TERMS
    except Exception:
        # fallback minimal set to avoid crash
        return {
            "Subjective (fallback)": ["easy", "user friendly"],
            "Option (fallback)": ["may", "can"],
        }

FUZZY_TERMS = _load_fuzzy_terms()

# ==== load invest thresholds for summary ====
def _load_invest_thresholds():
    try:
        from invest_rules import INVEST_THRESHOLDS
        return INVEST_THRESHOLDS
    except ModuleNotFoundError:
        here = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
        path = os.path.join(here, "invest_rules.py")
        if not os.path.exists(path):
            return {}
        spec = importlib.util.spec_from_file_location("invest_rules_dynamic", path)
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        assert spec and spec.loader
        spec.loader.exec_module(mod)  # type: ignore
        return getattr(mod, "INVEST_THRESHOLDS", {})

INVEST_THRESHOLDS = _load_invest_thresholds()

DIM_KEYS = ["I", "N", "V", "E", "S", "T"]

# ==== fuzzy detection ====
def _detect_fuzzy_terms(text: str) -> List[str]:
    hits: List[str] = []
    t = (text or "").lower()
    for category, terms in FUZZY_TERMS.items():
        src = "ISO 29148" if "ISO" in category else ("NASA ARM" if "NASA" in category else "")
        for term in terms:
            if re.search(r"\b" + re.escape(term.lower()) + r"\b", t):
                tag = f"{term} ({src})" if src else term
                hits.append(tag)
    # de-dup preserve order
    out, seen = [], set()
    for h in hits:
        if h not in seen:
            out.append(h); seen.add(h)
    return out

def _metrics_flat(m_before: Dict[str, Any], m_after: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in DIM_KEYS + ["overall"]:
        b = m_before.get(k, "")
        a = m_after.get(k, "")
        out[f"{k}_before"] = b
        out[f"{k}_after"]  = a
        try:
            out[f"delta_{k}"] = float(a) - float(b)
        except Exception:
            out[f"delta_{k}"] = ""
    return out

def _low_score_explanations(m_after: Dict[str, Any], cutoff: int = 2) -> str:
    reasons = m_after.get("reasons", {}) or {}
    lines = []
    for k in DIM_KEYS:
        try:
            if int(m_after.get(k, 0)) < cutoff:
                r = (reasons.get(k, "") or "").strip()
                if r:
                    lines.append(f"{k}: {r}")
        except Exception:
            pass
    return "\n".join(lines) if lines else "—"

def _index_results_by_id(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for i, r in enumerate(results):
        rid = str(r.get("id", f"row{i}"))
        out[rid] = r
    return out

# ==== export (wide) ====
def export_results_csv(results: List[Dict[str, Any]], out_root: str = "report") -> Tuple[pd.DataFrame, str]:
    """
    Creates /report/YYYYmmdd-HHMMSS/invest_report_*.csv
    Wide columns:
      ID | Original User Story | Rewritten User Story | Fuzzy Terms (with source)
      I_before I_after delta_I ... T_before T_after delta_T overall_before overall_after delta_overall
      Low-score Explanation (<2)
    """
    base_df = aggregate_results(results)  # keep your base shape if needed elsewhere
    os.makedirs(out_root, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = os.path.join(out_root, ts)
    os.makedirs(run_dir, exist_ok=True)

    res_by_id = _index_results_by_id(results)
    id_col = "id" if "id" in base_df.columns else None

    rows: List[Dict[str, Any]] = []
    for idx, row in base_df.iterrows():
        rid = str(row[id_col]) if id_col else f"row{idx}"
        r = res_by_id.get(rid, {})
        orig = r.get("original_text", "")
        final = r.get("final_text", "")
        reason = r.get("correction_reason", "—") # [新增] 讀取剛剛寫入的修正原因

        history = r.get("history") or []
        m_before = (history[0].get("metrics", {}) if history else {})
        m_after  = (history[-1].get("metrics", {}) if history else {})

        flat = _metrics_flat(m_before, m_after)
        fuzzy = _detect_fuzzy_terms(final)
        low_exp = _low_score_explanations(m_after, cutoff=2)

        wide = {
            "ID": rid,
            "Original User Story": orig,
            "Rewritten User Story": final,
            "Correction Reason": reason, 
            "Fuzzy Terms (with source)": "\n".join(fuzzy) if fuzzy else "—",
            "Low-score Explanation (<2)": low_exp,
        }
        wide.update(flat)
        rows.append(wide)

    # column order
    metric_cols = []
    for k in DIM_KEYS:
        metric_cols += [f"{k}_before", f"{k}_after", f"delta_{k}"]
    metric_cols += ["overall_before", "overall_after", "delta_overall"]

    cols = (
        ["ID", "Original User Story", "Rewritten User Story", "Correction Reason", "Fuzzy Terms (with source)"] 
        + metric_cols
        + ["Low-score Explanation (<2)"]
    )

    out_df = pd.DataFrame(rows, columns=cols)
    out_csv = os.path.join(run_dir, f"invest_report_{ts}.csv")
    out_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"✅ Report exported: {out_csv}  (rows={len(out_df)})")
    return out_df, run_dir

# ==== summary ====
def summarize_report(df: pd.DataFrame) -> Dict[str, Any]:
    summary = {"pass_rate": 0.0, "avg_rounds": 0.0, "delta_overall_mean": 0.0,
               "delta_dims_mean": {k: 0.0 for k in ["I","N","V","E","S","T"]}}
    if df.empty:
        print("⚠️ Empty report. Nothing to summarize."); return summary

    overall_cut = float(INVEST_THRESHOLDS.get("overall", 1.0))
    oa = pd.to_numeric(df.get("overall_after", 0), errors="coerce").fillna(0)
    summary["pass_rate"] = float((oa >= overall_cut).mean())

    if "rounds" in df.columns:
        rounds_col = pd.to_numeric(df["rounds"], errors="coerce").fillna(0)
        summary["avg_rounds"] = float(rounds_col.mean())
    else:
        summary["avg_rounds"] = 0.0

    if "delta_overall" in df.columns:
        summary["delta_overall_mean"] = float(pd.to_numeric(df["delta_overall"], errors="coerce").fillna(0).mean())

    for k in ["I","N","V","E","S","T"]:
        col = f"delta_{k}"
        if col in df.columns:
            vals = pd.to_numeric(df[col], errors="coerce").dropna()
            summary["delta_dims_mean"][k] = float(vals.mean()) if not vals.empty else 0.0

    print("\n=== Summary ===")
    print(f"✔️ Pass rate (overall_after ≥ {overall_cut}): {summary['pass_rate']:.2%}")
    print(f"🔁 Avg rounds: {summary['avg_rounds']:.2f}")
    print(f"📈 Avg ΔOverall: {summary['delta_overall_mean']:+.3f}")
    print("\nΔ per dimension (avg):")
    for k, v in summary["delta_dims_mean"].items():
        print(f"  {k}: {v:+.3f}")
    return summary
