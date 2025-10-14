"""
Pipeline for DSPy-based INVEST Optimization
-------------------------------------------
- 不使用 'title'
- 評分器 (InvestScorer) JSON 解析強化 + overall fallback
- 改寫器 (UserStoryRewriter) 固定輸出可驗證模板
- DSPy teleprompt：compile_scorer_with_teleprompt / compile_rewriter_with_teleprompt
- DEV 指標: objective_mean_delta_overall() 展示使用 DSPy 前/後差異
- Baseline 切換：USE_DSPY=0/1
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import json
import dspy
from tqdm import tqdm


# =========================
# 1) 少量種子資料（可改成讀檔）
# =========================

TRAIN_SEEDS = [
    {
        "input_text": (
            "As a user, I want to reset my password via email so that I can regain access.\n"
            "Acceptance Criteria:\n"
            "- Request reset link via email\n- Receive email\n- Reset succeeds"
        )
    },
    {"input_text": "Improve dashboard performance."},
]

DEV_SEEDS = [
    {
        "input_text": (
            "As an admin, I want to export users to CSV so that I can analyze data offline.\n"
            "Acceptance Criteria:\n"
            "- Button 'Export CSV'\n- Only active users\n- Fields accurate"
        )
    }
]


# =========================
# 2) DSPy Signatures
# =========================

class InvestScoreSig(dspy.Signature):
    """Grade a user story on INVEST (0–3) and return JSON (NO prose)."""
    input_text: str = dspy.InputField(desc=(
        "User story text. Reply ONLY with JSON: "
        '{"overall":int,"I":int,"N":int,"V":int,"E":int,"S":int,"T":int,'
        '"reasons":{"I":str,"N":str,"V":str,"E":str,"S":str,"T":str}} '
        "All scores are integers 0-3."
    ))
    result_json: str = dspy.OutputField(desc="Strict JSON per spec.")


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


# =========================
# 3) 模組
# =========================

class InvestScorer(dspy.Module):
    """LLM 評分器：呼叫一次 LLM 產生 JSON，並做強韌解析 + 範圍修正。"""
    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict(InvestScoreSig)

    def _clamp_int(self, v) -> int:
        try:
            v = int(float(v))
            return max(0, min(3, v))
        except Exception:
            return None

    def parse_json(self, raw: str) -> Dict[str, Any]:
        # parse JSON or best-effort extract
        try:
            obj = json.loads(raw)
        except Exception:
            try:
                start = raw.find("{")
                end   = raw.rfind("}")
                obj = json.loads(raw[start:end+1]) if start >= 0 and end >= 0 else {}
            except Exception:
                obj = {}

        dims = ["I", "N", "V", "E", "S", "T"]
        # normalize scores
        for k in ["overall", *dims]:
            obj[k] = self._clamp_int(obj.get(k))

        # overall fallback = round(mean(I..T))
        if obj.get("overall") is None:
            vals = [x for x in (obj.get(d) for d in dims) if x is not None]
            obj["overall"] = int(round(sum(vals)/len(vals))) if vals else 0

        # reasons
        if not isinstance(obj.get("reasons"), dict):
            obj["reasons"] = {}

        return obj

    def __call__(self, text: str) -> Dict[str, Any]:
        out = self.predict(input_text=text)
        return self.parse_json(out.result_json)


class UserStoryRewriter(dspy.Module):
    """LLM 改寫器：輸出固定模板以提高 Testable/Negotiable 等得分。"""
    def __init__(self):
        super().__init__()
        self.rewrite = dspy.Predict(InvestRewriteSig)

    def __call__(self, text: str) -> str:
        out = self.rewrite(input_text=text)
        return (out.improved_text or text).strip()


# =========================
# 4) Teleprompt 編譯（展示「可學」）
# =========================

def compile_scorer_with_teleprompt(base_scorer: "InvestScorer") -> "InvestScorer":
    # 用 base_scorer 先對 TRAIN_SEEDS 產生弱標註，當作 few-shot
    trainset = []
    for ex in TRAIN_SEEDS:
        y = base_scorer(ex["input_text"])
        trainset.append(
            dspy.Example(
                input_text=ex["input_text"],
                result_json=json.dumps(y, ensure_ascii=False)
            ).with_inputs("input_text")
        )
    try:
        tele = dspy.BootstrapFewShot(base_scorer.predict, max_bootstrapped_demos=min(6, len(trainset)))
        compiled = tele.compile(trainset=trainset)
        base_scorer.predict = compiled
    except Exception as e:
        print(f"[WARN] compile_scorer_with_teleprompt failed: {e}")
    return base_scorer


def compile_rewriter_with_teleprompt(base_rewriter: "UserStoryRewriter", scorer: "InvestScorer") -> "UserStoryRewriter":
    # 自動生成一小批 (src -> cand)，留下分數不下降的做 few-shot
    pairs: List[Tuple[str, str]] = []
    for ex in TRAIN_SEEDS:
        src = ex["input_text"]
        cand = base_rewriter(src)
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
            improved_text=(
                "User Story:\nAs a product analyst, I want initial dashboard load under 2s so that I can review KPIs quickly.\n"
                "Acceptance Criteria:\n- p95 cold start ≤ 2s\n- 6 widgets visible on load\n- Pagination for top lists\n"
                "Test Outline:\n- Synthetic dataset cold-start timing\n- Real data smoke test"
            )
        ).with_inputs("input_text")
    ]

    try:
        tele = dspy.BootstrapFewShot(base_rewriter.rewrite, max_bootstrapped_demos=min(6, len(trainset)))
        compiled = tele.compile(trainset=trainset)
        base_rewriter.rewrite = compiled
    except Exception as e:
        print(f"[WARN] compile_rewriter_with_teleprompt failed: {e}")
    return base_rewriter


# =========================
# 5) 指標函式（DEV 上的可量化比較）
# =========================

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


# =========================
# 6) 主流程
# =========================

@dataclass
class OptimizeConfig:
    max_rounds: int = 3
    fewshot_k: int = 4  # 預留；目前未直接使用
    use_dspy: bool = True


def run_batch_optimization(
    user_stories: List[Dict[str, Any]],
    max_rounds: int = 3,
    fewshot_k: int = 4,
    use_dspy: bool = True
) -> List[Dict[str, Any]]:
    """
    user_stories: [{"id":..., "description":...}, ...]
    return: list of {
        "id", "status", "rounds", "final_text",
        "history": [ {"text": str, "metrics": {overall,I..T,reasons}}, ... ]
    }
    """
    cfg = OptimizeConfig(max_rounds=max_rounds, fewshot_k=fewshot_k, use_dspy=use_dspy)

    # baseline modules
    base_scorer   = InvestScorer()
    base_rewriter = UserStoryRewriter()

    # compile with DSPy teleprompt if enabled
    if cfg.use_dspy:
        scorer   = compile_scorer_with_teleprompt(base_scorer)
        rewriter = compile_rewriter_with_teleprompt(base_rewriter, scorer)
        # DEV 指標（展示 DSPy 效益）
        before = objective_mean_delta_overall(InvestScorer(), UserStoryRewriter(), DEV_SEEDS)
        after  = objective_mean_delta_overall(scorer, rewriter, DEV_SEEDS)
        print(f"[DEV metric] ΔOverall baseline={before:+.3f} → with DSPy={after:+.3f}")
    else:
        scorer, rewriter = base_scorer, base_rewriter
        print("[DEV metric] DSPy disabled (USE_DSPY=0).")

    results: List[Dict[str, Any]] = []

    for story in tqdm(user_stories, desc="Optimizing User Stories"):
        text = story["description"]
        hist: List[Dict[str, Any]] = []

        # 初始評分
        m0 = scorer(text)
        hist.append({"text": text, "metrics": m0})

        # 多輪優化
        cur_text = text
        best_text, best_m = cur_text, m0

        for _ in range(cfg.max_rounds):
            # 產生最多兩個候選（best-of-2）
            candidates = []
            for _try in range(2):
                cand_text = rewriter(best_text)
                cand_m    = scorer(cand_text)
                hist.append({"text": cand_text, "metrics": cand_m})
                candidates.append((cand_text, cand_m))

            # 選擇 overall 分數最高的候選
            def score_of(m): 
                try: return int(m.get("overall") or 0)
                except: return 0
            winner_text, winner_m = max(candidates, key=lambda p: score_of(p[1]))

            # 若有提升就接受，否則保留最佳並嘗試下一輪
            if score_of(winner_m) > score_of(best_m):
                best_text, best_m = winner_text, winner_m

            # 早停：已達 3 分
            if score_of(best_m) >= 3:
                break

        results.append({
            "id": story["id"],
            "status": "done",
            "rounds": max(0, len(hist) - 1),  # 改寫評分次數
            "final_text": best_text,
            "history": hist
        })

    return results
