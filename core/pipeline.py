from __future__ import annotations
"""
pipeline.py — DSPy-based INVEST Optimizer (robustly loads invest_rules.py)
- First attempts a normal import of invest_rules; if that fails, uses importlib to load by filename.
- Rewriter: performs significant rewrites, avoids copying the original phrasing, targets >=30% token-level difference.
- Scorer: fuses LLM (60%) + heuristic rubric (40%); overall score follows INVEST_WEIGHTS.
- Selection: uses INVEST score + λ * Jaccard diversity; supports MIN_DIVERSITY.
- DEV: prints overall and mean Δ for each dimension.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import os, json, re, importlib.util, types
from tqdm import tqdm
import dspy

# ========= Load invest_rules.py =========
def _load_invest_rules():
    
    try:
        from invest_rules import INVEST_RUBRIC, INVEST_THRESHOLDS, INVEST_WEIGHTS
        return INVEST_RUBRIC, INVEST_THRESHOLDS, INVEST_WEIGHTS
    except ModuleNotFoundError:
        pass

    
    here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    candidates = [
        os.path.join(here, "invest_rules.py"),
        os.path.join(here, "invest rules.py"),
        os.path.join(here, "..", "invest_rules.py"),
        os.path.join(here, "..", "invest rules.py"),
    ]
    for p in candidates:
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("invest_rules_local", p)
            mod = importlib.util.module_from_spec(spec)  # type: ignore
            assert spec and spec.loader
            spec.loader.exec_module(mod)  # type: ignore
            return mod.INVEST_RUBRIC, mod.INVEST_THRESHOLDS, mod.INVEST_WEIGHTS

    raise ModuleNotFoundError(
        "invest_rules.py not found. Please ensure:\n"
        "1) it is in the same directory as pipeline.py, or\n"
        "2) you run from the directory that contains invest_rules.py, or\n"
        "3) invest_rules.py is on your PYTHONPATH."
    )

INVEST_RUBRIC, INVEST_THRESHOLDS, INVEST_WEIGHTS = _load_invest_rules()

# =========================
# LM settings fallback
# =========================
def configure_default_lm():
    try:
        lm = getattr(dspy.settings, "lm", None)
    except Exception:
        lm = None
    if lm is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[WARN] OPENAI_API_KEY 未設定。請 export OPENAI_API_KEY。")
        print("[INFO] Configuring default LM: openai/gpt-4o-mini (temperature=0.8)")
        dspy.settings.configure(
            lm=dspy.LM(
                "openai/gpt-4o-mini",
                api_key=api_key,
                temperature=0.8,
                max_tokens=512
            )
        )


configure_default_lm()

# ===== seeds =====
TRAIN_SEEDS = [
    {"input_text": "As a user, I want to reset my password via email so that I can regain access.\nAcceptance Criteria:\n- Request reset link via email\n- Receive email\n- Reset succeeds"},
    {"input_text": "Improve dashboard performance.\nAcceptance Criteria:\n- Current p95=5s; target p95<=2s\n- Reduce initial DB calls to <=8\n- Cache top 3 widgets on first paint"}
]
DEV_SEEDS = [
    {"input_text": "As an admin, I want to export users to CSV so that I can analyze data offline.\nAcceptance Criteria:\n- Button 'Export CSV'\n- Only active users\n- Fields accurate"}
]

# ===== env flags / knobs =====
STRICT = os.getenv("USE_STRICT_INVEST", "0") == "1"
USE_DSPY = os.getenv("USE_DSPY", "1") != "0"
DIVERSITY_LAMBDA = float(os.getenv("DIVERSITY_LAMBDA", "0.7"))
MIN_DIVERSITY    = float(os.getenv("MIN_DIVERSITY", "0.30"))

# ===== token utils for diversity =====
def _tokens(s: str):
    return re.findall(r"[A-Za-z0-9]+", s.lower())

def jaccard_diversity(a: str, b: str) -> float:
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 0.0
    return 1.0 - (len(ta & tb) / len(ta | tb))

# ===== Signatures =====
class InvestScoreSig(dspy.Signature):
    """Grade a user story on INVEST (0–3); return JSON only, using the rubric (Annex A spirit)."""
    input_text: str = dspy.InputField(desc=(
        "You are an INVEST rater. Score I,N,V,E,S,T on 0–3 using THIS rubric:\n"
        "- I: 0=no; 1=entangled; 2=mostly standalone; 3=single clear goal.\n"
        "- N: 0=technical spec; 1=functional spec; 2=requirements shared; 3=high-level need enabling feedback.\n"
        "- V: 0=no value; 1=implied; 2=explicit but generic; 3=explicit business-relevant benefit.\n"
        "- E: 0=vague; 1=some hints; 2=bounded by quality/tech; 3=well-bounded with numbers/constraints validated.\n"
        "- S: 0=epic; 1=too broad; 2=medium; 3=small enough for a sprint.\n"
        "- T: 0=no tests; 1=tests indicated but incomplete; 2=complete but unvalidated; 3=completed and validated tests.\n"
        "Reply ONLY with JSON: "
        '{"overall":int,"I":int,"N":int,"V":int,"E":int,"S":int,"T":int,'
        '"reasons":{"I":str,"N":str,"V":str,"E":str,"S":str,"T":str}} '
        + ("Scoring is STRICT: any vagueness caps ≤2; 3 requires explicit & measurable evidence."
           if STRICT else "Give 3 only when explicit & measurable evidence is present.")
    ))
    result_json: str = dspy.OutputField(desc="Strict JSON as specified.")

class InvestRewriteSig(dspy.Signature):
    """Rewrite the story to improve INVEST while keeping intent (significantly rephrase)."""
    input_text: str = dspy.InputField()
    improved_text: str = dspy.OutputField(desc=(
        "Rewrite with SIGNIFICANT rephrase (avoid copying >8 consecutive words). "
        "Use stronger, specific verbs/nouns. Keep intent but clarify role/capability/benefit. "
        "Aim for >=30% token-level difference from the input.\n"
        "Output EXACTLY in this template:\n"
        "User Story:\nAs a <specific role>, I want <clear capability> so that <explicit, business-relevant benefit>.\n"
        "Acceptance Criteria:\n"
        "- <measurable criterion 1>\n- <measurable criterion 2>\n- <measurable criterion 3>\n"
        "Test Outline:\n- <how to verify 1>\n- <how to verify 2>"
    ))

# ===== Modules =====
class InvestScorer(dspy.Module):
    LLM_WEIGHT = 0.6
    HEU_WEIGHT = 0.4

    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict(InvestScoreSig)

    # --- utils ---
    def _clamp_int(self, v):
        try:
            v = int(float(v)); return max(0, min(3, v))
        except Exception:
            return None
    def _lines(self, s: str): return [x.strip() for x in s.splitlines()]
    def _sec(self, s: str, header: str) -> bool: return header.lower() in s.lower()
    def _count_bullets_after(self, s: str, header: str) -> int:
        lines = self._lines(s)
        try:
            idx = next(i for i,ln in enumerate(lines) if header.lower() in ln.lower())
        except StopIteration:
            return 0
        cnt = 0
        for ln in lines[idx+1:]:
            if ln.startswith("- "): cnt += 1
            elif ln.endswith(":"): break
        return cnt
    def _count_numbers(self, s: str) -> int:
        return len(re.findall(r'\b\d+(?:\.\d+)?\b', s))
    def _has_cmp(self, s: str) -> bool:
        return any(sym in s for sym in ["≤","≥","<=",">=","<",">","%"," s"," ms"])
    def _story_core(self, s: str) -> str:
        m = re.search(r"As a .*? so that .*?(?:\.|\n|$)", s, flags=re.IGNORECASE|re.DOTALL)
        return m.group(0) if m else s.split("\n",1)[0]

    # --- heuristic from rubric ---
    def heuristic_scores_from_rubric(self, text: str) -> Tuple[Dict[str,int], Dict[str,str]]:
        t = text.strip()
        core = self._story_core(t)
        has_role_iwant = bool(re.search(r"As a .*?,?\s*I want", core, re.IGNORECASE))
        has_so_that    = ("so that" in core.lower())
        has_ac         = self._sec(t, "Acceptance Criteria")
        n_ac           = self._count_bullets_after(t, "Acceptance Criteria")
        has_test_sec   = self._sec(t, "Test Outline") or self._sec(t, "Test Plan")
        has_test_word  = (" test" in (" " + t.lower()))
        n_nums         = self._count_numbers(t)
        has_cmp        = self._has_cmp(t)
        story_len      = len(_tokens(core))
        rigid_markers  = ["must ","exactly ","pixel","ui spec","api spec","endpoint:","fixed layout","hard-coded","strictly","no deviation"]
        is_rigid       = any(m in t.lower() for m in rigid_markers)

        I = 3 if has_role_iwant and (" and " not in core.lower()) else (2 if has_role_iwant else 1)
        if is_rigid:
            N = 0 if any(x in t.lower() for x in ["ui spec","api spec","endpoint:"]) else 1
        else:
            N = 3 if (has_ac and not is_rigid) else (2 if not is_rigid else 1)
        V = 3 if has_so_that else (2 if (" to " in core.lower()) else 1)
        if n_nums>=2 or (n_nums>=1 and has_cmp): E = 3
        elif n_nums>=1 or has_ac:                E = 2
        else:                                    E = 1
        S = 3 if story_len<=30 else (2 if story_len<=60 else 1)
        if has_ac and (has_test_sec or has_test_word) and (n_nums>0 or has_cmp) and n_ac>=2: T = 3
        elif has_ac and n_ac>=1:                                                        T = 2
        else:                                                                           T = 1
        if STRICT:
            if E==3 and n_nums==0 and not has_cmp: E = 2
            if T==3 and not (n_nums>0 or has_cmp): T = 2

        scores  = {"I":I,"N":N,"V":V,"E":E,"S":S,"T":T}
        reasons = {
            "I": f"single-goal={(' and ' not in core.lower())}; has As a/I want={has_role_iwant}",
            "N": f"rigid_spec={is_rigid}; has_AC={has_ac}",
            "V": f"has_benefit_clause(so that)={has_so_that}",
            "E": f"numbers={n_nums}; comparators={has_cmp}; has_AC={has_ac}",
            "S": f"story_token_len={story_len}",
            "T": f"AC_bullets={n_ac}; test_sec/word={has_test_sec or has_test_word}; measurable={n_nums>0 or has_cmp}",
        }
        return scores, reasons

    # --- parse LLM json ---
    def parse_json(self, raw_json: str) -> Dict[str, Any]:
        try:
            obj = json.loads(raw_json)
        except Exception:
            try:
                s, e = raw_json.find("{"), raw_json.rfind("}")
                obj = json.loads(raw_json[s:e+1]) if s>=0 and e>=0 else {}
            except Exception:
                obj = {}
        dims = ["I","N","V","E","S","T"]
        for k in ["overall", *dims]:
            obj[k] = self._clamp_int(obj.get(k))
        if not isinstance(obj.get("reasons"), dict):
            obj["reasons"] = {}
        return obj

    def _weighted_overall(self, dim_scores: Dict[str,int]) -> float:
        num = sum(dim_scores[d]*INVEST_WEIGHTS.get(d,1) for d in ["I","N","V","E","S","T"])
        den = sum(INVEST_WEIGHTS.get(d,1) for d in ["I","N","V","E","S","T"])
        return num/den if den else 0.0

    # --- fuse LLM + heuristic ---
    def fuse(self, llm_obj: Dict[str,Any], heu: Dict[str,int], text: str) -> Dict[str,Any]:
        dims = ["I","N","V","E","S","T"]
        out: Dict[str,Any] = {"reasons": {}}
        for d in dims:
            l = llm_obj.get(d)
            h = heu.get(d, 0)
            val = h if l is None else round(self.LLM_WEIGHT*l + self.HEU_WEIGHT*h)
            if STRICT and val>2 and d in ["E","T"]:
                if (self._count_numbers(text)==0 and not self._has_cmp(text)):
                    val = 2
            out[d] = int(val)

        weighted = self._weighted_overall(out)
        if STRICT:
            floor_by_dims = min(out[d] for d in dims)
            out["overall"] = int(round(min(weighted, floor_by_dims)))
        else:
            out["overall"] = int(round(weighted))

        out["meets_thresholds"] = {
            d: (out[d] >= int(round(INVEST_THRESHOLDS.get(d, 0))))
            for d in ["I","N","V","E","S","T"]
        }
        out["meets_thresholds"]["overall"] = (out["overall"] >= int(round(INVEST_THRESHOLDS.get("overall", 0))))

        for d in dims:
            llm_r = (llm_obj.get("reasons") or {}).get(d)
            out["reasons"][d] = (llm_r or "")
        return out

    def __call__(self, text: str) -> Dict[str, Any]:
        llm_out = self.predict(input_text=text)
        llm_obj = self.parse_json(llm_out.result_json)
        heu_scores, heu_reasons = self.heuristic_scores_from_rubric(text)
        fused = self.fuse(llm_obj, heu_scores, text)
        for d in ["I","N","V","E","S","T"]:
            prefix = (" | " if fused["reasons"].get(d) else "")
            fused["reasons"][d] = (fused["reasons"].get(d) or "") + prefix + f"HEU: {heu_reasons[d]}"
        return fused

class UserStoryRewriter(dspy.Module):
    def __init__(self):
        super().__init__()
        self.rewrite = dspy.Predict(InvestRewriteSig)
    def __call__(self, text: str) -> str:
        out = self.rewrite(input_text=text)
        return (out.improved_text or text).strip()

# ===== Teleprompt =====
def compile_scorer_with_teleprompt(base_scorer: InvestScorer, fewshot_k: int = 4, max_rounds: int = 1, metric_fn=None, teacher_lm=None) -> InvestScorer:
    trainset = []
    for ex in TRAIN_SEEDS:
        y = base_scorer(ex["input_text"])
        trainset.append(dspy.Example(input_text=ex["input_text"], result_json=json.dumps(y, ensure_ascii=False)).with_inputs("input_text"))
    try:
        tele = dspy.BootstrapFewShot(metric=metric_fn, max_labeled_demos=min(fewshot_k, len(trainset)),
                                     max_bootstrapped_demos=min(4, len(trainset)), max_rounds=max_rounds,
                                     teacher_settings=({"lm": teacher_lm} if teacher_lm else None))
        compiled = tele.compile(student=base_scorer.predict, trainset=trainset)
        base_scorer.predict = compiled
    except Exception as e:
        print(f"[WARN] compile_scorer_with_teleprompt failed: {e}")
    return base_scorer

def compile_rewriter_with_teleprompt(base_rewriter: UserStoryRewriter, scorer: InvestScorer, fewshot_k: int = 4, max_rounds: int = 1, metric_fn=None, teacher_lm=None) -> UserStoryRewriter:
    pairs: List[Tuple[str, str]] = []
    for ex in TRAIN_SEEDS:
        src = ex["input_text"]; cand = base_rewriter(src)
        m0, m1 = scorer(src), scorer(cand)
        try:
            if int(m1.get("overall") or 0) >= int(m0.get("overall") or 0):
                pairs.append((src, cand))
        except Exception:
            pass
    trainset = [dspy.Example(input_text=s, improved_text=t).with_inputs("input_text") for (s,t) in pairs] or [
        dspy.Example(input_text="Improve dashboard performance.",
                     improved_text=("User Story:\nAs a product analyst, I want initial dashboard load under 2s so that I can review KPIs quickly.\n"
                                    "Acceptance Criteria:\n- p95 cold start ≤ 2s\n- 6 widgets visible on load\n- Pagination for top lists\n"
                                    "Test Outline:\n- Synthetic dataset cold-start timing\n- Real data smoke test")).with_inputs("input_text")
    ]
    try:
        tele = dspy.BootstrapFewShot(metric=metric_fn, max_labeled_demos=min(fewshot_k, len(trainset)),
                                     max_bootstrapped_demos=min(4, len(trainset)), max_rounds=max_rounds,
                                     teacher_settings=({"lm": teacher_lm} if teacher_lm else None))
        compiled = tele.compile(student=base_rewriter.rewrite, trainset=trainset)
        base_rewriter.rewrite = compiled
    except Exception as e:
        print(f"[WARN] compile_rewriter_with_teleprompt failed: {e}")
    return base_rewriter

# ===== DEV metrics =====
def objective_mean_delta_overall(scorer: InvestScorer, rewriter: UserStoryRewriter, dev_items: List[Dict[str, Any]]) -> float:
    deltas: List[int] = []
    for ex in dev_items:
        src = ex["input_text"]
        m0  = scorer(src)
        new = rewriter(src)
        m1  = scorer(new)
        try:
            deltas.append(int(m1.get("overall") or 0) - int(m0.get("overall") or 0))
        except Exception:
            continue
    return float(sum(deltas) / len(deltas)) if deltas else 0.0

def dimension_deltas_report(scorer: InvestScorer, rewriter: UserStoryRewriter, dev_items: List[Dict[str, Any]]) -> Dict[str, float]:
    dims = ["I","N","V","E","S","T","overall"]
    agg = {d: [] for d in dims}
    for ex in dev_items:
        src = ex["input_text"]
        m0  = scorer(src)
        new = rewriter(src)
        m1  = scorer(new)
        for d in dims:
            try:
                agg[d].append(int(m1.get(d) or 0) - int(m0.get(d) or 0))
            except Exception:
                pass
    return {d: (sum(agg[d])/len(agg[d]) if agg[d] else 0.0) for d in dims}

# ===== main runner =====
@dataclass
class OptimizeConfig:
    max_rounds: int = 3
    fewshot_k: int = 4
    use_dspy: bool = True
    best_of_k: int = 3
    diversity_lambda: float = DIVERSITY_LAMBDA
    min_diversity:    float = MIN_DIVERSITY

def run_batch_optimization(user_stories: List[Dict[str, Any]], max_rounds: int = 3, fewshot_k: int = 4, use_dspy: bool = True, best_of_k: int = 3, diversity_lambda: Optional[float] = None, min_diversity: Optional[float] = None) -> List[Dict[str, Any]]:
    cfg = OptimizeConfig(max_rounds=max_rounds, fewshot_k=fewshot_k, use_dspy=use_dspy, best_of_k=best_of_k,
                         diversity_lambda=(diversity_lambda if diversity_lambda is not None else DIVERSITY_LAMBDA),
                         min_diversity=(min_diversity if min_diversity is not None else MIN_DIVERSITY))

    base_scorer   = InvestScorer()
    base_rewriter = UserStoryRewriter()

    if cfg.use_dspy:
        scorer   = compile_scorer_with_teleprompt(base_scorer, fewshot_k=cfg.fewshot_k, max_rounds=cfg.max_rounds)
        rewriter = compile_rewriter_with_teleprompt(base_rewriter, scorer, fewshot_k=cfg.fewshot_k, max_rounds=cfg.max_rounds)
        before = objective_mean_delta_overall(InvestScorer(), UserStoryRewriter(), DEV_SEEDS)
        after  = objective_mean_delta_overall(scorer, rewriter, DEV_SEEDS)
        print(f"[DEV] ΔOverall baseline={before:+.3f} → with DSPy={after:+.3f}")
        deltas = dimension_deltas_report(scorer, rewriter, DEV_SEEDS)
        print("[DEV] mean Δ by dimension:", {k: round(v,3) for k,v in deltas.items()})
    else:
        scorer, rewriter = base_scorer, base_rewriter
        print("[DEV] DSPy disabled (USE_DSPY=0).")

    results: List[Dict[str, Any]] = []
    for story in tqdm(user_stories, desc="Optimizing User Stories"):
        original_text = story["description"]
        hist: List[Dict[str, Any]] = []

        m0 = scorer(original_text)
        hist.append({"text": original_text, "metrics": m0, "diversity": 0.0})

        best_text, best_m = original_text, m0
        best_combo = int(m0.get("overall") or 0) + cfg.diversity_lambda * 0.0

        def invest_overall(m: Dict[str, Any]) -> int:
            try: return int(m.get("overall") or 0)
            except: return 0

        for _ in range(cfg.max_rounds):
            candidates = []
            for _try in range(cfg.best_of_k):
                cand_text = base_rewriter(original_text) if _try == 0 else base_rewriter(best_text)
                cand_m    = scorer(cand_text)
                div       = jaccard_diversity(original_text, cand_text)
                hist.append({"text": cand_text, "metrics": cand_m, "diversity": div})
                candidates.append((cand_text, cand_m, div))

            def combo_score(item) -> float:
                _, m, div = item
                return invest_overall(m) + cfg.diversity_lambda * div

            elig = [c for c in candidates if c[2] >= cfg.min_diversity] or candidates
            winner_text, winner_m, winner_div = max(elig, key=combo_score)
            winner_combo = combo_score((winner_text, winner_m, winner_div))

            if winner_combo > best_combo:
                best_text, best_m, best_combo = winner_text, winner_m, winner_combo

            if invest_overall(best_m) >= 3 and jaccard_diversity(original_text, best_text) >= cfg.min_diversity:
                break

        results.append({
            "id": story.get("id"),
            "status": "done",
            "rounds": max(0, len(hist) - 1),
            "original_text": original_text,
            "final_text": best_text,
            "history": hist
        })
    return results

# ===== Example =====
if __name__ == "__main__":
    sample_batch = [
        {"id": "ex1", "description": "I want to describe myself on my own page in a semi-structured way, so that others can learn about me."},
        {"id": "ex2", "description": "Improve dashboard performance."},
    ]
    out = run_batch_optimization(sample_batch, max_rounds=3, fewshot_k=4, use_dspy=USE_DSPY)
    print(json.dumps(out, ensure_ascii=False, indent=2))
