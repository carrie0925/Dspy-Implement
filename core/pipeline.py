from __future__ import annotations
"""
pipeline.py — DSPy-based INVEST Optimizer (1–5 scale, diversity + teleprompt)
- Loads INVEST_RUBRIC_15 / INVEST_THRESHOLDS / INVEST_WEIGHTS from invest_rules.py
- Rewriter: ≥30% token-level difference, then subject-only role lock (keep persona)
- Scorer: LLM(75%) + Heuristic(25%), all on 1–5 scale, overall uses INVEST_WEIGHTS
- Selection: INVEST overall + λ * Jaccard diversity (min diversity enforced)
- Early stop: uses INVEST_THRESHOLDS["overall"] (not hard-coded 3)
- Outputs: original/rewritten, rubric text, fuzzy terms, low-score notes, final scores
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import os, json, re, importlib.util
from tqdm import tqdm
import dspy

# ========= Load invest_rules.py =========
def _load_invest_rules():
    try:
        from invest_rules import INVEST_RUBRIC_15, INVEST_THRESHOLDS, INVEST_WEIGHTS
        return INVEST_RUBRIC_15, INVEST_THRESHOLDS, INVEST_WEIGHTS
    except ModuleNotFoundError:
        pass

    here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    for p in [
        os.path.join(here, "invest_rules.py"),
        os.path.join(here, "invest rules.py"),
        os.path.join(here, "..", "invest_rules.py"),
        os.path.join(here, "..", "invest rules.py"),
    ]:
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("invest_rules_local", p)
            mod = importlib.util.module_from_spec(spec)  # type: ignore
            assert spec and spec.loader
            spec.loader.exec_module(mod)  # type: ignore
            return mod.INVEST_RUBRIC_15, mod.INVEST_THRESHOLDS, mod.INVEST_WEIGHTS

    raise ModuleNotFoundError("invest_rules.py not found near pipeline.py or on PYTHONPATH.")

INVEST_RUBRIC_15, INVEST_THRESHOLDS, INVEST_WEIGHTS = _load_invest_rules()

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
print(f"[DEBUG] USE_DSPY={USE_DSPY}, STRICT={STRICT}, DIVERSITY_LAMBDA={DIVERSITY_LAMBDA}, MIN_DIVERSITY={MIN_DIVERSITY}")

# ===== tiny call counters (for sanity check) =====
CALLS = {"scorer": 0, "rewriter": 0}

# ===== token & diversity utils =====
def _tokens(s: str):
    return re.findall(r"[A-Za-z0-9]+", s.lower())

def jaccard_diversity(a: str, b: str) -> float:
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 0.0
    return 1.0 - (len(ta & tb) / len(ta | tb))

def token_diff_ratio(a: str, b: str) -> float:
    """Estimate rewrite magnitude via token-set Jaccard distance."""
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 1.0 if (a.strip() and not b.strip()) or (b.strip() and not a.strip()) else 0.0
    return 1.0 - (len(ta & tb) / len(ta | tb))

# ===== Role lock helpers (SUBJECT-ONLY REPLACEMENT) =====
def _extract_us_line(block: str) -> str:
    for ln in block.splitlines():
        if ln.strip().lower().startswith("as "):
            return ln.strip()
    return (block.splitlines()[0] if block.strip() else "").strip()

# NOTE: comma is optional now (',?')
_ROLE_HEAD_RE = re.compile(
    r"^(?P<prefix>\s*As\s+a?n?\s+)"
    r"(?P<role>[^,]+)"
    r"(?P<suffix>,?\s*I\b.*)$",
    re.IGNORECASE
)

def _lock_role(original_text: str, rewritten_text: str) -> tuple[str, dict]:
    """
    Replace only the <role> in rewritten's first 'As ...' line with original's <role>.
    Keep rewritten's verb (want/aim/plan...) and connectors (so that / in order to ...).
    """
    orig_us = _extract_us_line(original_text)
    new_us  = _extract_us_line(rewritten_text)

    head_old = _ROLE_HEAD_RE.match(orig_us or "")
    head_new = _ROLE_HEAD_RE.match(new_us or "")

    if head_old and head_new:
        fixed_us = f"{head_old.group('prefix')}{head_old.group('role')}{head_new.group('suffix')}"
        lines = rewritten_text.splitlines()
        replaced = False
        for i, ln in enumerate(lines):
            if ln.strip() == new_us:
                lines[i] = fixed_us
                replaced = True
                break
        if not replaced:
            if lines:
                lines[0] = fixed_us
            else:
                lines = [fixed_us]
        return "\n".join(lines), {"role_locked": True, "reason": "subject_only_replaced"}

    return rewritten_text, {"role_locked": False, "reason": "parse_failed_head"}

# ===== Fuzzy term detection (lightweight lexical set) =====
LEXICON = {
    "VERB_VAGUE": ["improve", "enhance", "optimize", "support", "handle", "leverage", "streamline"],
    "ADJ_VAGUE":  ["easy", "fast", "robust", "reliable", "scalable", "user-friendly", "intuitive", "seamless"],
    "ADV_VAGUE":  ["quickly", "easily", "significantly", "efficiently", "reliably"],
    "QTY_VAGUE":  ["many", "some", "few", "several", "various", "as needed"],
    "TIME_VAGUE": ["soon", "ASAP", "later", "instantly", "in real-time"],
    "PLACEHOLDER":["etc.", "tbd", "to be decided", "and so on"],
}
_HAS_NUM = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*(?:ms|s|sec|seconds?|minutes?|hours?|%|x)?\b)|(?:<=|>=|=|>|<)",
    re.IGNORECASE
)

def _mk_suggestion(token: str) -> str:
    return f"Replace '{token}' with a measurable criterion (e.g., '<= 200 ms', 'p95 <= 2s', explicit scope/boundary')."

def detect_fuzzy(text: str) -> List[Dict[str, Any]]:
    spans: List[Dict[str, Any]] = []
    for pos, words in LEXICON.items():
        for w in words:
            for m in re.finditer(rf"\b{re.escape(w)}\b", text, flags=re.IGNORECASE):
                sentence_start = text.rfind('.', 0, m.start()) + 1
                sentence_end = text.find('.', m.end())
                if sentence_end == -1: sentence_end = len(text)
                sent = text[sentence_start:sentence_end]
                if not _HAS_NUM.search(sent):
                    spans.append({
                        "text": w, "pos": pos,
                        "reason": "Ambiguous or non-verifiable term without measurable threshold in the same sentence.",
                        "suggestion": _mk_suggestion(w),
                        "start": m.start(), "end": m.end()
                    })
    return spans

# ===== Low-score explanation =====
EXPLANATION_TEMPLATES = {
    "I": {"why": "Story depends on other stories or mixed goals.", "fix": ["Split by goal; remove cross-dependencies in AC."]},
    "N": {"why": "Prescriptive solution; scope not negotiable.", "fix": ["Focus on outcomes, not implementation; allow alternatives."]},
    "V": {"why": "Persona value unclear.", "fix": ["Rewrite 'so that' with explicit, business-relevant benefit."]},
    "E": {"why": "Effort unbounded; constraints missing.", "fix": ["Add numeric thresholds/assumptions/risks in AC."]},
    "S": {"why": "Too large for a sprint.", "fix": ["Slice by platform, data case, or exception path; target 2–3 days."]},
    "T": {"why": "Lacks objective test conditions.", "fix": ["Add Gherkin-style AC with measurable thresholds and boundary cases."]},
}
def explain_low_scores(scores: Dict[str, Any], threshold: float = 3.0) -> Dict[str, Any]:
    out = {}
    for dim, meta in EXPLANATION_TEMPLATES.items():
        try:
            val = int(scores.get(dim) or 0)
        except Exception:
            val = 0
        if val < threshold:
            out[dim] = {"score": val, "why_low": meta["why"], "how_to_fix": meta["fix"]}
    return out

def rubric_as_text() -> str:
    parts = []
    for k in ["I","N","V","E","S","T"]:
        meta = INVEST_RUBRIC_15.get(k, {})
        nm = meta.get("name", k)
        desc = meta.get("description", "")
        parts.append(f"{k}-{nm}: {desc}")
    return " | ".join(parts)

# ===== Signatures =====
class InvestScoreSig(dspy.Signature):
    """Grade a user story on INVEST (1–5); return JSON only, using this rubric summary."""
    input_text: str = dspy.InputField(desc=(
        "Score I,N,V,E,S,T on 1–5 using THIS rubric summary:\n"
        "- I: 1=strongly tied/blocked; 3=some constraints; 5=fully independent single-goal.\n"
        "- N: 1=technical spec/no negotiation; 3=requirement but limited flexibility; 5=high-level need enabling feedback.\n"
        "- V: 1=function lacks user value; 3=value implied/generic; 5=explicit, user/ business-relevant benefit.\n"
        "- E: 1=vague effort; 3=some hints; 4=bounded; 5=measurable with numbers/constraints validated.\n"
        "- S: 1=epic; 3=medium; 5=small enough for a Sprint (balanced dev/test).\n"
        "- T: 1=no tests; 3=tests indicated; 4=complete; 5=completed & validated acceptance tests.\n"
        "Reply ONLY with JSON: "
        '{"overall":int,"I":int,"N":int,"V":int,"E":int,"S":int,"T":int,'
        '"reasons":{"I":str,"N":str,"V":str,"E":str,"S":str,"T":str}} '
        + ("Scoring is STRICT: 5 needs explicit & measurable evidence; otherwise cap at 4."
           if STRICT else "Give 5 only when explicit & measurable evidence is present.")
    ))
    result_json: str = dspy.OutputField(desc="Strict JSON as specified.")

class InvestRewriteSig(dspy.Signature):
    """Rewrite the story to improve INVEST while keeping intent (significantly rephrase)."""
    input_text: str = dspy.InputField()
    improved_text: str = dspy.OutputField(desc=(
        "Rewrite with SIGNIFICANT rephrase (≥30% token difference). "
        "Strengthen all INVEST dimensions explicitly; keep the same persona but clarify capability and value. "
        "Prefer measurable, falsifiable criteria (numbers, %, ≤, ≥). "
        "Output EXACTLY in this template:\n"
        "User Story:\nAs a <specific role>, I want <clear capability> so that <explicit, business-relevant benefit>.\n"
        "Acceptance Criteria:\n"
        "- <measurable criterion 1>\n- <measurable criterion 2>\n- <measurable criterion 3>\n"
        "Test Outline:\n- <how to verify 1>\n- <how to verify 2>"
    ))

# ===== Modules =====
import dspy
import re
import json
from typing import Tuple, Dict, Any

# --- 假設的外部依賴項 (您需要提供這些) ---
# 您需要確保 dspy 已經被正確導入
# 並且 InvestScoreSig 已經被定義 (例如: class InvestScoreSig(dspy.Signature): ...)
# 以及 _tokens, STRICT, CALLS, INVEST_WEIGHTS, INVEST_THRESHOLDS 這些變數
# ----------------------------------------------------

class InvestScorer(dspy.Module):
    # --- MODIFIED: 提高 LLM 權重, 降低啟發式權重 (75%/25%) ---
    LLM_WEIGHT = 0.75
    HEU_WEIGHT = 0.25

    def __init__(self):
        super().__init__()
        self.predict = dspy.Predict(InvestScoreSig) # 假設 InvestScoreSig 已定義

    # --- utils (與您提供的版本相同) ---
    def _clamp_int15(self, v):
        try:
            v = int(float(v)); return max(1, min(5, v))
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
    
    # ========================================================================
    # --- MODIFIED: (V3) 嚴格對應 INVEST_RUBRIC_15 ---
    # (這是我們在上一則訊息中最終確定的版本，用來取代 V2 邏輯)
    # ========================================================================
    def heuristic_scores_from_rubric(self, text: str) -> Tuple[Dict[str,int], Dict[str,str]]:
        t = text.strip()
        low = t.lower()
        core = self._story_core(t) # 假設 _story_core() 已定義

        # --- 提取特徵 ---
        has_role_iwant = bool(re.search(r"As a .*?,?\s*I want|As a .*?,?\s*I\b", core, re.IGNORECASE))
        single_goal    = (" and " not in core.lower())
        has_so_that    = ("so that" in core.lower()) or ("in order to" in core.lower())
        
        has_ac         = self._sec(t, "Acceptance Criteria")
        n_ac           = self._count_bullets_after(t, "Acceptance Criteria")
        
        has_test_sec   = self._sec(t, "Test Outline") or self._sec(t, "Test Plan")
        has_test_word  = (" test" in (" " + low))
        
        n_nums         = self._count_numbers(t) # 假設 _count_numbers() 已定義
        has_cmp        = self._has_cmp(t)       # 假設 _has_cmp() 已定義
        is_measurable  = (n_nums > 0 or has_cmp)
        
        story_len      = len(_tokens(core)) # 假設 _tokens() 已定義
        rigid_markers  = ["must ","exactly ","pixel","ui spec","api spec","endpoint:","fixed layout","hard-coded","strictly","no deviation"]
        is_rigid       = any(m in low for m in rigid_markers)

        # --- 根據 Rubric 1-5 嚴格評分 ---

        # I (Independent) - Rubric 1-3: 依賴/不清楚
        I = 5 if (has_role_iwant and single_goal) else \
            (3 if has_role_iwant else 2) # 基礎分 2 (Rubric 2: "independence is unclear")

        # N (Negotiable) - Rubric 1: "prescriptive", Rubric 2: "minimal context", Rubric 3: "requires... refinement"
        if is_rigid:
            N = 1 # Rubric 1: "overly prescriptive"
        elif has_ac and any(w in low for w in ["feedback","negotiate","shared"]):
            N = 5 # Rubric 5 (proxy)
        elif has_ac:
            N = 3 # Rubric 3: 有 AC, "requires collaborative refinement"
        else:
            N = 2 # Rubric 2: 沒有 AC = "minimal context", "ambiguous"

        # V (Valuable) - Rubric 1: "no value", Rubric 3: "qualitative... lacks measurable", Rubric 5: "measurable"
        if has_so_that and is_measurable:
            V = 5 # Rubric 5: "explicit, measurable"
        elif has_so_that:
            V = 3 # Rubric 3: "clear qualitative... but lacks measurable"
        elif " to " in core.lower():
            V = 2 # Rubric 2: "value... remains fuzzy"
        else:
            V = 1 # Rubric 1: "little or no user-visible value"

        # E (Estimable) - Rubric 1: "lacks sufficient clarity", Rubric 4: "well-defined... functional logic", Rubric 5: "fully detailed"
        if has_ac and is_measurable and n_ac >= 2:
            E = 5 # Rubric 5: "fully detailed" (AC + measurable + multiple)
        elif has_ac and n_ac >= 1:
            E = 4 # Rubric 4: "well-defined" (有 AC)
        elif "assumption" in low or "constraint" in low:
            E = 3 # Rubric 3: "coarse estimate but still requires clarification"
        elif is_measurable: # 有數字但沒 AC
            E = 2 # Rubric 2: "partly understandable... highly uncertain"
        else:
            E = 1 # Rubric 1: "lacks sufficient clarity" (沒 AC 也沒數字)

        # S (Small) - (邏輯不變, Sizing 依賴 token 數是合理的)
        S = 5 if story_len <= 30 else \
            (4 if story_len <= 60 else \
            (3 if story_len <= 100 else 2)) # 基礎分 2

        # T (Testable) - Rubric 1: "lacks any AC", Rubric 3: "partial... tests", Rubric 5: "fully validated"
        if has_ac and has_test_sec and n_ac >= 2:
            T = 5 # Rubric 5 (proxy: AC + Test Outline)
        elif has_ac and n_ac >= 2:
            T = 4 # Rubric 4: "clear, verifiable" (多個 AC)
        elif has_ac and n_ac == 1:
            T = 3 # Rubric 3: "partial or draft" (單個 AC)
        elif has_test_word:
            T = 2 # Rubric 2: "references expected behavior but no concrete tests"
        else:
            T = 1 # Rubric 1: "lacks any acceptance criteria"

        # 假設 STRICT 已定義
        if STRICT: 
            if E == 5 and not is_measurable: E = 4
            if T == 5 and not is_measurable: T = 4

        scores  = {"I":I,"N":N,"V":V,"E":E,"S":S,"T":T}
        reasons = {
            "I": f"single_goal={single_goal}; has_As/I...={has_role_iwant}",
            "N": f"rigid_spec={is_rigid}; has_AC={has_ac} (bullets: {n_ac})",
            "V": f"benefit_clause(so that/in order to)={has_so_that}; measurable={is_measurable}",
            "E": f"has_AC={has_ac} (bullets: {n_ac}); measurable={is_measurable}",
            "S": f"story_token_len={story_len}",
            "T": f"has_AC={has_ac} (bullets: {n_ac}); has_Test_Outline={has_test_sec}",
        }
        return scores, reasons
    # ========================================================================
    # --- 啟發式規則 V3 結束 ---
    # ========================================================================

    # --- parse LLM json (與您提供的版本相同) ---
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
            obj[k] = self._clamp_int15(obj.get(k))
        if not isinstance(obj.get("reasons"), dict):
            obj["reasons"] = {}
        return obj

    # --- _weighted_overall (與您提供的版本相同) ---
    def _weighted_overall(self, dim_scores: Dict[str,int]) -> float:
        # 假設 INVEST_WEIGHTS 已定義
        num = sum(dim_scores[d]*INVEST_WEIGHTS.get(d,1) for d in ["I","N","V","E","S","T"])
        den = sum(INVEST_WEIGHTS.get(d,1) for d in ["I","N","V","E","S","T"])
        return num/den if den else 0.0

    # --- fuse (與您提供的版本相同, 但會使用新的 LLM_WEIGHT) ---
    def fuse(self, llm_obj: Dict[str,Any], heu: Dict[str,int], text: str) -> Dict[str,Any]:
        dims = ["I","N","V","E","S","T"]
        out: Dict[str,Any] = {"reasons": {}}
        for d in dims:
            l = llm_obj.get(d)
            h = heu.get(d, 0)
            val = h if l is None else round(self.LLM_WEIGHT*l + self.HEU_WEIGHT*h)
            if STRICT and val>4 and d in ["E","T"]: # 假設 STRICT 已定義
                if (self._count_numbers(text)==0 and not self._has_cmp(text)):
                    val = 4
            out[d] = int(max(1, min(5, val)))

        weighted = self._weighted_overall(out)
        out["overall"] = int(round(weighted))

        # 假設 INVEST_THRESHOLDS 已定義
        out["meets_thresholds"] = {
            d: (out[d] >= int(round(INVEST_THRESHOLDS.get(d, 3))))
            for d in ["I","N","V","E","S","T"]
        }
        out["meets_thresholds"]["overall"] = (out["overall"] >= int(round(INVEST_THRESHOLDS.get("overall", 3))))

        for d in dims:
            llm_r = (llm_obj.get("reasons") or {}).get(d)
            out["reasons"][d] = (llm_r or "")
        return out

    # --- __call__ (與您提供的版本相同) ---
    def __call__(self, text: str) -> Dict[str, Any]:
        # 假設 CALLS 已定義
        CALLS["scorer"] += 1
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
        CALLS["rewriter"] += 1
        MIN_DIFF = 0.30
        MAX_TRIES = 3
        best = text
        for _ in range(MAX_TRIES):
            out = self.rewrite(input_text=best)
            rewritten = (getattr(out, "improved_text", None) or best).strip()
            rewritten, _meta = _lock_role(text, rewritten)
            if token_diff_ratio(text, rewritten) >= MIN_DIFF:
                return rewritten
            best = rewritten
        return best

# ===== Teleprompt =====
def compile_scorer_with_teleprompt(base_scorer: InvestScorer, fewshot_k: int = 4, max_rounds: int = 1, metric_fn=None, teacher_lm=None) -> InvestScorer:
    trainset = []
    for ex in TRAIN_SEEDS:
        y = base_scorer(ex["input_text"])
        trainset.append(dspy.Example(input_text=ex["input_text"], result_json=json.dumps(y, ensure_ascii=False)).with_inputs("input_text"))
    print(f"[DEBUG] scorer teleprompt trainset size = {len(trainset)}")

    try:
        tele = dspy.BootstrapFewShot(metric=metric_fn, max_labeled_demos=min(fewshot_k, len(trainset)),
                                     max_bootstrapped_demos=min(4, len(trainset)), max_rounds=max_rounds,
                                     teacher_settings=({"lm": teacher_lm} if teacher_lm else None))
        print("[DEBUG] starting scorer teleprompt.compile()")
        compiled = tele.compile(student=base_scorer.predict, trainset=trainset)
        base_scorer.predict = compiled
        print("[DEBUG] scorer teleprompt.compile() finished OK")
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
    print(f"[DEBUG] rewriter teleprompt pairs size = {len(pairs)}")

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
        print("[DEBUG] starting rewriter teleprompt.compile()")
        compiled = tele.compile(student=base_rewriter.rewrite, trainset=trainset)
        base_rewriter.rewrite = compiled
        print("[DEBUG] rewriter teleprompt.compile() finished OK")
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


def run_batch_optimization(
    user_stories: List[Dict[str, Any]],
    max_rounds: int = 3,
    fewshot_k: int = 4,
    use_dspy: bool = USE_DSPY,
    best_of_k: int = 3,
    diversity_lambda: Optional[float] = None,
    min_diversity: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Core optimization workflow (detailed):

    - Instantiate a base scorer and rewriter. If use_dspy is enabled, compile them
      with a small DSPy few-shot / teleprompt training pass using TRAIN_SEEDS so the
      student LLM behaviors are improved before batch processing.

    - For each user story, run up to max_rounds of iterative rewrite + scoring:
      * In each round generate up to best_of_k candidate rewrites. The first
        candidate in the first try is seeded from the original text; subsequent
        tries may seed from the current best text to explore local refinements.
      * Score every candidate with the scorer and compute token-level Jaccard
        diversity relative to the original. Record each candidate into a history
        list with its metrics and diversity value.

    - Candidate selection:
      * Compute a combo objective = INVEST_overall(candidate) + diversity_lambda * diversity.
      * Enforce a minimum diversity cutoff (min_diversity). If no candidates meet
        the minimum, fall back to considering all candidates.
      * Choose the winner with the highest combo objective.

    - Rounds accounting and early stopping:
      * The variable rounds_used counts only rounds where the chosen winner
        produced a genuine improvement in the combo objective (i.e., the best
        combo increased). This makes the reported "rounds" reflect actual gains.
      * Stop iterating early for a story if the current best meets or exceeds the
        INVEST overall threshold and also satisfies the minimum diversity
        requirement relative to the original.

    - After finishing iterations for a story:
      * Detect fuzzy / non-measurable terms in the final text.
      * Generate low-score explanations for any INVEST dimensions below the
        configured threshold.
      * Assemble and append the final result record (history, final text, scores,
        fuzzy terms, explanations, etc.) to the batch results.

    This docstring explains the exact semantics used by the loop below so callers
    understand how candidates are generated, when rounds are counted, and what
    triggers early termination.
    """
    cfg = OptimizeConfig(
        max_rounds=max_rounds,
        fewshot_k=fewshot_k,
        use_dspy=use_dspy,
        best_of_k=best_of_k,
        diversity_lambda=(diversity_lambda if diversity_lambda is not None else DIVERSITY_LAMBDA),
        min_diversity=(min_diversity if min_diversity is not None else MIN_DIVERSITY),
    )

    print(
        f"[DEBUG] run_batch_optimization use_dspy={cfg.use_dspy}, "
        f"max_rounds={cfg.max_rounds}, fewshot_k={cfg.fewshot_k}, "
        f"best_of_k={cfg.best_of_k}, diversity_lambda={cfg.diversity_lambda}, "
        f"min_diversity={cfg.min_diversity}"
    )

    base_scorer   = InvestScorer()
    base_rewriter = UserStoryRewriter()

    # === 先用少量 seed 讓 DSPy 調 scorer / rewriter ===
    if cfg.use_dspy:
        print("[DEBUG] DSPy teleprompt branch enabled.")
        scorer   = compile_scorer_with_teleprompt(
            base_scorer,
            fewshot_k=cfg.fewshot_k,
            max_rounds=cfg.max_rounds,
        )
        rewriter = compile_rewriter_with_teleprompt(
            base_rewriter,
            scorer,
            fewshot_k=cfg.fewshot_k,
            max_rounds=cfg.max_rounds,
        )

        # 在 DEV_SEEDS 上看一下 baseline vs 優化後差多少
        before = objective_mean_delta_overall(InvestScorer(), UserStoryRewriter(), DEV_SEEDS)
        after  = objective_mean_delta_overall(scorer, rewriter, DEV_SEEDS)
        print(f"[DEV] ΔOverall baseline={before:+.3f} → with DSPy={after:+.3f}")
        deltas = dimension_deltas_report(scorer, rewriter, DEV_SEEDS)
        print("[DEV] mean Δ by dimension:", {k: round(v, 3) for k, v in deltas.items()})
    else:
        scorer, rewriter = base_scorer, base_rewriter
        print("[DEV] DSPy disabled (USE_DSPY=0).")

    def invest_overall(m: Dict[str, Any]) -> int:
        try:
            return int(m.get("overall") or 0)
        except Exception:
            return 0

    stop_at = int(round(INVEST_THRESHOLDS.get("overall", 3)))

    results: List[Dict[str, Any]] = []

    for story in tqdm(user_stories, desc="Optimizing User Stories"):
        original_text = story["description"]
        hist: List[Dict[str, Any]] = []

        # baseline 評分
        m0 = scorer(original_text)
        hist.append({"text": original_text, "metrics": m0, "diversity": 0.0})

        best_text, best_m = original_text, m0
        best_combo = invest_overall(m0) + cfg.diversity_lambda * 0.0

        rounds_used = 0  # ✅ 實際「有提升」的輪數

        # === 多輪改寫迴圈 ===
        for _round in range(cfg.max_rounds):
            candidates = []

            for _try in range(cfg.best_of_k):
                # 第一次用 original，之後用當前 best 當 seed 改寫
                seed_text = original_text if _try == 0 else best_text
                cand_text = rewriter(seed_text)
                cand_m    = scorer(cand_text)
                div       = jaccard_diversity(original_text, cand_text)

                hist.append({
                    "text": cand_text,
                    "metrics": cand_m,
                    "diversity": div,
                })
                candidates.append((cand_text, cand_m, div))

            if not candidates:
                break

            def combo_score(item) -> float:
                _, m, div = item
                return invest_overall(m) + cfg.diversity_lambda * div

            elig = [c for c in candidates if c[2] >= cfg.min_diversity] or candidates
            winner_text, winner_m, winner_div = max(elig, key=combo_score)
            winner_combo = combo_score((winner_text, winner_m, winner_div))

            if winner_combo > best_combo:
                best_text, best_m, best_combo = winner_text, winner_m, winner_combo
                rounds_used += 1  

            if invest_overall(best_m) >= stop_at and jaccard_diversity(original_text, best_text) >= cfg.min_diversity:
                break

        # === 結果整理 ===
        fuzzy_terms = detect_fuzzy(best_text)
        low_notes   = explain_low_scores(best_m, threshold=3.0)

        results.append({
            "id": story.get("id"),
            "status": "done",
            "rounds": rounds_used,                 
            "original_text": original_text,
            "final_text": best_text,
            "history": hist,

            "original": original_text,
            "rewritten": best_text,
            "scoring_criteria_text": rubric_as_text(),
            "fuzzy_terms": fuzzy_terms,
            "low_score_explanations": low_notes,
            "score_new": best_m,
        })

    return results


# ===== Example / CSV export if available =====
if __name__ == "__main__":
    sample_batch = [
        {"id": "ex1", "description": "As a site member I want to fill out an application to become a Certified Scrum Trainer so that I can teach CSM and CSPO courses and certify others."},
        {"id": "ex2", "description": "Improve dashboard performance."},
    ]
    out = run_batch_optimization(sample_batch, max_rounds=3, fewshot_k=4, use_dspy=USE_DSPY)
    print("[STATS] LLM calls → scorer:", CALLS["scorer"], "rewriter:", CALLS["rewriter"])
    try:
        from report_generator import export_results_csv
        df, run_dir = export_results_csv(out, out_root="report")
        print("[OK] CSV saved at:", run_dir)
    except Exception:
        try:
            from core.report_generator import export_results_csv
            df, run_dir = export_results_csv(out, out_root="report")
            print("[OK] CSV saved at:", run_dir)
        except Exception as e:
            print("[INFO] report_generator not found or export failed; printing JSON instead.")
            print(json.dumps(out, ensure_ascii=False, indent=2))