"""
Pipeline for DSPy-based INVEST Optimization (no 'title')
Adds: strict scoring via USE_STRICT_INVEST, returns original_text.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import os, json
import dspy
from tqdm import tqdm

# ===== seeds =====
TRAIN_SEEDS = [
    {"input_text": "As a user, I want to reset my password via email so that I can regain access.\nAcceptance Criteria:\n- Request reset link via email\n- Receive email\n- Reset succeeds"},
    {"input_text": "Improve dashboard performance."},
]
DEV_SEEDS = [
    {"input_text": "As an admin, I want to export users to CSV so that I can analyze data offline.\nAcceptance Criteria:\n- Button 'Export CSV'\n- Only active users\n- Fields accurate"}
]

# ===== env flags =====
STRICT = os.getenv("USE_STRICT_INVEST", "0") == "1"

# ===== Signatures =====
class InvestScoreSig(dspy.Signature):
    """Grade a user story on INVEST (0–3); return JSON only."""
    input_text: str = dspy.InputField(desc=(
        "User story text. Reply ONLY with JSON: "
        '{"overall":int,"I":int,"N":int,"V":int,"E":int,"S":int,"T":int,'
        '"reasons":{"I":str,"N":str,"V":str,"E":str,"S":str,"T":str}} '
        + ("Scoring is STRICT: 3=explicit & measurable criteria; any vagueness caps a dimension at ≤2."
           if STRICT else "Use 3 only for clear & measurable criteria.")
    ))
    result_json: str = dspy.OutputField(desc="Strict JSON as specified.")

class InvestRewriteSig(dspy.Signature):
    """Rewrite the story to improve INVEST while keeping intent."""
    input_text: str = dspy.InputField()
    improved_text: str = dspy.OutputField(desc=(
        "Rewrite to improve INVEST. Output exactly in this template:\n"
        "User Story:\nAs a <role>, I want <capability> so that <benefit>.\n"
        "Acceptance Criteria:\n"
        "- <measurable criterion 1>\n- <measurable criterion 2>\n- <measurable criterion 3>\n"
        "Test Outline:\n- <how to verify 1>\n- <how to verify 2>"
    ))

# ===== Modules =====
class InvestScorer(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict(InvestScoreSig)

    def _clamp_int(self, v):
        try:
            v = int(float(v)); return max(0, min(3, v))
        except Exception:
            return None

    def parse_json(self, raw: str) -> Dict[str, Any]:
        try:
            obj = json.loads(raw)
        except Exception:
            try:
                s, e = raw.find("{"), raw.rfind("}")
                obj = json.loads(raw[s:e+1]) if s >= 0 and e >= 0 else {}
            except Exception:
                obj = {}
        dims = ["I","N","V","E","S","T"]
        for k in ["overall", *dims]:
            obj[k] = self._clamp_int(obj.get(k))
        # overall fallback
        vals = [obj[d] for d in dims if obj[d] is not None]
        if obj.get("overall") is None:
            if STRICT and vals:
                obj["overall"] = min(vals)                # 更嚴格：瓶頸主導
            elif vals:
                obj["overall"] = int(round(sum(vals)/len(vals)))
            else:
                obj["overall"] = 0
        if not isinstance(obj.get("reasons"), dict):
            obj["reasons"] = {}
        # 在嚴格模式下，若某維度無明確驗證語句，將 T 或相關維度降至 ≤2（簡易啟發式）
        if STRICT and obj.get("T") == 3:
            text = raw.lower()
            if ("acceptance" not in text and "criteria" not in text and "test" not in text):
                obj["T"] = 2
                obj["overall"] = min(obj["overall"], 2)
        return obj

    def __call__(self, text: str) -> Dict[str, Any]:
        out = self.predict(input_text=text)
        return self.parse_json(out.result_json)

class UserStoryRewriter(dspy.Module):
    def __init__(self):
        super().__init__()
        self.rewrite = dspy.Predict(InvestRewriteSig)
    def __call__(self, text: str) -> str:
        out = self.rewrite(input_text=text)
        return (out.improved_text or text).strip()

# ===== Teleprompt (新版 DSPy 需要 student) =====
def compile_scorer_with_teleprompt(base_scorer: "InvestScorer") -> "InvestScorer":
    trainset = []
    for ex in TRAIN_SEEDS:
        y = base_scorer(ex["input_text"])
        trainset.append(dspy.Example(input_text=ex["input_text"],
                                     result_json=json.dumps(y, ensure_ascii=False)
                                     ).with_inputs("input_text"))
    try:
        tele = dspy.BootstrapFewShot(k=min(6, len(trainset)))
        compiled = tele.compile(student=base_scorer.predict, trainset=trainset)
        base_scorer.predict = compiled
    except Exception as e:
        print(f"[WARN] compile_scorer_with_teleprompt failed: {e}")
    return base_scorer

def compile_rewriter_with_teleprompt(base_rewriter: "UserStoryRewriter", scorer: "InvestScorer") -> "UserStoryRewriter":
    pairs: List[Tuple[str, str]] = []
    for ex in TRAIN_SEEDS:
        src = ex["input_text"]; cand = base_rewriter(src)
        m0, m1 = scorer(src), scorer(cand)
        try:
            if int(m1.get("overall") or 0) >= int(m0.get("overall") or 0):
                pairs.append((src, cand))
        except Exception:
            pass
    trainset = [
        dspy.Example(input_text=s, improved_text=t).with_inputs("input_text")
        for (s, t) in pairs
    ] or [
        dspy.Example(
            input_text="Improve dashboard performance.",
            improved_text=("User Story:\nAs a product analyst, I want initial dashboard load under 2s so that I can review KPIs quickly.\n"
                           "Acceptance Criteria:\n- p95 cold start ≤ 2s\n- 6 widgets visible on load\n- Pagination for top lists\n"
                           "Test Outline:\n- Synthetic dataset cold-start timing\n- Real data smoke test")
        ).with_inputs("input_text")
    ]
    try:
        tele = dspy.BootstrapFewShot(k=min(6, len(trainset)))
        compiled = tele.compile(student=base_rewriter.rewrite, trainset=trainset)
        base_rewriter.rewrite = compiled
    except Exception as e:
        print(f"[WARN] compile_rewriter_with_teleprompt failed: {e}")
    return base_rewriter

# ===== DEV metric =====
def objective_mean_delta_overall(scorer: "InvestScorer", rewriter: "UserStoryRewriter", dev_items: List[Dict[str, Any]]) -> float:
    deltas = []
    for ex in dev_items:
        src = ex["input_text"]
        m0  = scorer(src)
        new = rewriter(src)
        m1  = scorer(new)
        try:
            a = int(m0.get("overall") or 0)
            b = int(m1.get("overall") or 0)
            deltas.append(b - a)
        except Exception:
            continue
    return sum(deltas) / len(deltas) if deltas else 0.0

# ===== main runner =====
@dataclass
class OptimizeConfig:
    max_rounds: int = 3
    fewshot_k: int = 4
    use_dspy: bool = True

def run_batch_optimization(
    user_stories: List[Dict[str, Any]],
    max_rounds: int = 3,
    fewshot_k: int = 4,
    use_dspy: bool = True
) -> List[Dict[str, Any]]:
    cfg = OptimizeConfig(max_rounds=max_rounds, fewshot_k=fewshot_k, use_dspy=use_dspy)

    base_scorer   = InvestScorer()
    base_rewriter = UserStoryRewriter()

    if cfg.use_dspy:
        scorer   = compile_scorer_with_teleprompt(base_scorer)
        rewriter = compile_rewriter_with_teleprompt(base_rewriter, scorer)
        before = objective_mean_delta_overall(InvestScorer(), UserStoryRewriter(), DEV_SEEDS)
        after  = objective_mean_delta_overall(scorer, rewriter, DEV_SEEDS)
        print(f"[DEV metric] ΔOverall baseline={before:+.3f} → with DSPy={after:+.3f}")
    else:
        scorer, rewriter = base_scorer, base_rewriter
        print("[DEV metric] DSPy disabled (USE_DSPY=0).")

    results: List[Dict[str, Any]] = []

    for story in tqdm(user_stories, desc="Optimizing User Stories"):
        original_text = story["description"]
        hist: List[Dict[str, Any]] = []

        m0 = scorer(original_text)
        hist.append({"text": original_text, "metrics": m0})

        cur_text = original_text
        best_text, best_m = cur_text, m0

        for _ in range(cfg.max_rounds):
            candidates = []
            for _try in range(2):  # best-of-2
                cand_text = rewriter(best_text)
                cand_m    = scorer(cand_text)
                hist.append({"text": cand_text, "metrics": cand_m})
                candidates.append((cand_text, cand_m))

            def score_of(m): 
                try: return int(m.get("overall") or 0)
                except: return 0
            winner_text, winner_m = max(candidates, key=lambda p: score_of(p[1]))

            if score_of(winner_m) > score_of(best_m):
                best_text, best_m = winner_text, winner_m
            if score_of(best_m) >= 3:
                break

        results.append({
            "id": story["id"],
            "status": "done",
            "rounds": max(0, len(hist) - 1),
            "original_text": original_text,   # ← 新增：給報表用
            "final_text": best_text,
            "history": hist
        })

    return results
