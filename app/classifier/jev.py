import logging
import re
from typing import List, Optional, Dict, Any
import httpx
from app.models import ChatMessage
from .base import BaseClassifier
from .types import ClassificationResult, ModelTier
from .rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)

# Max candidate models evaluated per Jev call: bounds payload size/latency.
MAX_FIT_CANDIDATES = 6


def _slugify(model_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(model_id).lower()).strip("_")


def _build_fit_question(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Build a per-model fit question tailored to the candidate's profile."""
    model_id = str(candidate.get("id", "unknown"))
    name = str(candidate.get("name", model_id))
    provider = str(candidate.get("provider", "unknown"))
    tier = str(candidate.get("tier", "unknown"))
    price_in = candidate.get("price_in")
    price_out = candidate.get("price_out")
    context_length = candidate.get("context_length")
    scores = candidate.get("scores") or {}

    price_txt = (
        f"Input ${price_in}/MTok, output ${price_out}/MTok"
        if price_in is not None and price_out is not None
        else "pricing unknown"
    )
    context_txt = f"{context_length:,} tokens".replace(",", " ") if context_length else "unknown"
    if isinstance(scores, dict) and scores:
        bench_txt = ", ".join(f"{k}: {v}" for k, v in list(scores.items())[:5])
    else:
        bench_txt = "no benchmark data"

    return {
        "type": "score",
        "instructions": (
            f"Rate how well suited the model '{name}' (provider: {provider}, tier: {tier}) "
            f"is for THIS request. Context window: {context_txt}, Pricing: {price_txt}. "
            f"Benchmarks: [{bench_txt}]. "
            "Consider: 1) Is the cost justified for this request? Prefer cheaper models for simple tasks. "
            "2) Does the model's capabilities (from benchmarks) align with the prompt's requirements? "
            "3) Will the context length suffice? "
            "Provide a score from 0.0 to 1.0 reflecting the optimal balance of cost, capability, and constraints."
        ),
        "criteria": [
            "0.0-0.3: poor fit (overkill cost, underpowered, or mismatched capabilities)",
            "0.4-0.7: acceptable fit (viable but not the ideal balance)",
            "0.8-1.0: strong fit (excellent balance of cost, capability, and constraints)",
        ],
    }

TIER_MAPPING: Dict[str, ModelTier] = {
    "cheap": ModelTier.CHEAP,
    "low": ModelTier.CHEAP,
    "medium": ModelTier.MEDIUM,
    "frontier": ModelTier.FRONTIER,
    "high": ModelTier.FRONTIER,
}


class JevClassifier(BaseClassifier):
    """
    TypeSafe AI 'Jev' System One classifier adapter.
    Evaluates context against structured questions via POST /v1/systemone.
    Gracefully falls back to RuleBasedClassifier if credentials are unset or the remote service is unreachable.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.typesafe.ai/v1",
        model: str = "jev-latest",
        timeout: float = 5.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.fallback = RuleBasedClassifier()
        if not self.api_key:
            logger.warning(
                "JevClassifier initialized without JEV_API_KEY. "
                "Requests will fall back to rule-based mock classification."
            )

    def _get_endpoint_url(self) -> str:
        url = self.base_url
        if url.endswith("/systemone"):
            return url
        if not url.endswith("/v1"):
            return f"{url}/v1/systemone"
        return f"{url}/systemone"

    def _build_payload(
        self,
        messages: List[ChatMessage],
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        questions: Dict[str, Any] = {
            "tier": {
                "type": "choice",
                "instructions": "Determine the optimal LLM model tier (cheap, medium, or frontier) to handle this conversation/request based on complexity, reasoning depth, and technical requirements. Focus on minimizing cost without sacrificing quality.",
                "criteria": {
                    "cheap": "Simple, routine queries, greetings, basic facts, straightforward translations or summaries. Low risk of failure.",
                    "medium": "Moderate complexity, intermediate tasks, multi-step instructions, standard code snippets, structured outputs.",
                    "frontier": "Complex reasoning, advanced coding, system architecture, mathematical proofs, deep technical troubleshooting, nuance-heavy creative tasks."
                }
            },
            "complexity": {
                "type": "score",
                "instructions": "Rate the overall technical and reasoning complexity of the request from 0.0 (simplest) to 1.0 (hardest).",
                "criteria": [
                    "0.0-0.3: Low complexity - routine, factual, conversational.",
                    "0.4-0.7: Moderate complexity - multi-step, structural, analytical.",
                    "0.8-1.0: High complexity - intricate reasoning, novel problem-solving, advanced algorithms."
                ]
            },
            "domain": {
                "type": "choice",
                "instructions": "Identify the primary domain or topic of the request.",
                "criteria": {
                    "code_engineering": "Programming, software development, debugging, system design.",
                    "data_engineering": "Data manipulation, SQL, ETL, analytics.",
                    "complex_reasoning": "Math, logic, puzzles, deep analysis.",
                    "creative_writing": "Storytelling, poetry, ideation, drafting content.",
                    "content_summary": "Summarization, extraction, parsing.",
                    "conversational": "General chat, greetings, casual interaction."
                }
            }
        }
        # Per-model fit questions, tailored to each candidate's profile
        # (pricing, context window, benchmark scores). Bounded to keep the
        # payload small and the Jev call fast.
        for candidate in (candidates or [])[:MAX_FIT_CANDIDATES]:
            if not isinstance(candidate, dict) or not candidate.get("id"):
                continue
            key = f"fit_{_slugify(candidate['id'])}"
            questions[key] = _build_fit_question(candidate)

        return {
            "model": self.model,
            "state": {
                "messages": [m.model_dump() for m in messages]
            },
            "questions": questions,
        }

    def _parse_response(
        self,
        data: Dict[str, Any],
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> ClassificationResult:
        # 1. Official TypeSafe SystemOne response structure
        if "answers" in data and isinstance(data["answers"], dict):
            answers = data["answers"]
            tier_answer = answers.get("tier", {})
            choice = str(tier_answer.get("choice", "cheap")).lower().strip()
            tier = TIER_MAPPING.get(choice, ModelTier.CHEAP)

            confidence = float(tier_answer.get("confidence", 0.90))
            confidence = max(0.0, min(1.0, confidence))

            complexity_answer = answers.get("complexity", {})
            raw_score = complexity_answer.get("score")
            if raw_score is not None:
                # 3 levels (indices 0, 1, 2) normalized to 0.0 - 1.0
                score = float(raw_score) / 2.0
            elif "probabilities" in tier_answer and isinstance(tier_answer["probabilities"], dict):
                probs = tier_answer["probabilities"]
                p_frontier = probs.get("frontier", probs.get("high", 0.0))
                p_medium = probs.get("medium", 0.0)
                p_cheap = probs.get("cheap", probs.get("low", 0.0))
                score = p_frontier * 1.0 + p_medium * 0.5 + p_cheap * 0.1
            else:
                score = 0.90 if tier == ModelTier.FRONTIER else (0.50 if tier == ModelTier.MEDIUM else 0.15)
            score = max(0.0, min(1.0, score))

            reasons = [f"TypeSafe Jev routed to '{tier.value}' tier (choice: {choice}, confidence: {confidence:.2f})"]
            probabilities = {}
            if "probabilities" in tier_answer and isinstance(tier_answer["probabilities"], dict):
                raw_p = tier_answer["probabilities"]
                p_c = float(raw_p.get("cheap", raw_p.get("low", 0.0)))
                p_m = float(raw_p.get("medium", 0.0))
                p_f = float(raw_p.get("frontier", raw_p.get("high", 0.0)))
                tot = p_c + p_m + p_f
                if tot > 0:
                    probabilities = {
                        "cheap": round(p_c / tot, 4),
                        "medium": round(p_m / tot, 4),
                        "frontier": round(p_f / tot, 4),
                    }
                probs_str = ", ".join(f"{k}: {v:.2f}" for k, v in tier_answer["probabilities"].items())
                reasons.append(f"Jev tier probabilities: {probs_str}")
            if not probabilities:
                probabilities = RuleBasedClassifier._calculate_probabilities(score)

            if raw_score is not None:
                reasons.append(f"Jev complexity score: {float(raw_score):.2f}")

            # Per-model fit scores from the tailored fit_* questions.
            model_fit: Dict[str, float] = {}
            if candidates:
                slug_to_id = {
                    f"fit_{_slugify(c.get('id', ''))}": str(c.get("id"))
                    for c in candidates
                    if isinstance(c, dict) and c.get("id")
                }
                for key, mid in slug_to_id.items():
                    ans = answers.get(key, {})
                    if isinstance(ans, dict) and ans.get("score") is not None:
                        try:
                            model_fit[mid] = round(max(0.0, min(1.0, float(ans["score"]))), 3)
                        except (TypeError, ValueError):
                            continue
            best_fit_model = max(model_fit, key=model_fit.get) if model_fit else None
            if best_fit_model:
                reasons.append(
                    f"Best model fit: '{best_fit_model}' (fit score: {model_fit[best_fit_model]:.2f})"
                )

            return ClassificationResult(
                tier=tier,
                confidence=round(confidence, 2),
                score=round(score, 3),
                reasons=reasons,
                suggested_model=tier.value,
                probabilities=probabilities,
                metadata={
                    "provider": "typesafe_jev",
                    "model": data.get("model", self.model),
                    "usage": data.get("usage", {}),
                    "model_fit": model_fit,
                    "best_fit_model": best_fit_model,
                }
            )

        # 2. Legacy / simplified response fallback
        raw_tier = str(data.get("tier", "cheap")).lower().strip()
        tier = TIER_MAPPING.get(raw_tier, ModelTier.CHEAP)
        score_val = float(data.get("score", 0.50))
        return ClassificationResult(
            tier=tier,
            confidence=float(data.get("confidence", 0.90)),
            score=score_val,
            reasons=data.get("reasons", [f"Classified by TypeSafe AI Jev ({tier.value})"]),
            suggested_model=data.get("suggested_model", tier.value),
            probabilities=RuleBasedClassifier._calculate_probabilities(score_val),
            metadata={
                "provider": "typesafe_jev",
                "model": data.get("model", self.model),
                "usage": data.get("usage", {})
            }
        )

    def classify(
        self,
        messages: List[ChatMessage],
        strategy: str = "balanced",
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> ClassificationResult:
        if not messages:
            return ClassificationResult(
                tier=ModelTier.CHEAP,
                confidence=1.0,
                score=0.0,
                reasons=["Empty message context routed to cheap tier by default"],
                suggested_model="cheap",
                probabilities={"cheap": 0.85, "medium": 0.12, "frontier": 0.03},
                metadata={"provider": "typesafe_jev"}
            )

        if not self.api_key:
            logger.warning("JevClassifier: JEV_API_KEY is not set. Falling back to rule-based mock classifier.")
            res = self.fallback.classify(messages, strategy=strategy, candidates=candidates)
            res.metadata["provider"] = "jev_mock_fallback"
            res.reasons.insert(0, "[Jev Fallback] JEV_API_KEY not configured; evaluated via rule-based classifier")
            return res

        url = self._get_endpoint_url()
        payload = self._build_payload(messages, candidates=candidates)

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                return self._parse_response(data, candidates=candidates)
        except Exception as e:
            logger.warning("Jev API request failed (%s: %s). Falling back to rule-based mock classifier.", type(e).__name__, e)
            res = self.fallback.classify(messages, strategy=strategy, candidates=candidates)
            res.metadata["provider"] = "jev_error_fallback"
            res.reasons.insert(0, f"[Jev Warning] Fallback activated ({type(e).__name__}: {e})")
            return res

    async def classify_async(
        self,
        messages: List[ChatMessage],
        strategy: str = "balanced",
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> ClassificationResult:
        if not messages:
            return ClassificationResult(
                tier=ModelTier.CHEAP,
                confidence=1.0,
                score=0.0,
                reasons=["Empty message context routed to cheap tier by default"],
                suggested_model="cheap",
                metadata={"provider": "typesafe_jev"}
            )

        if not self.api_key:
            logger.warning("JevClassifier: JEV_API_KEY is not set. Falling back to rule-based mock classifier.")
            res = self.fallback.classify(messages, strategy=strategy, candidates=candidates)
            res.metadata["provider"] = "jev_mock_fallback"
            res.reasons.insert(0, "[Jev Fallback] JEV_API_KEY not configured; evaluated via rule-based classifier")
            return res

        url = self._get_endpoint_url()
        payload = self._build_payload(messages, candidates=candidates)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                resp.raise_for_status()
                data = resp.json()
                return self._parse_response(data, candidates=candidates)
        except Exception as e:
            logger.warning("Async Jev API request failed (%s: %s). Falling back to rule-based mock classifier.", type(e).__name__, e)
            res = self.fallback.classify(messages, strategy=strategy, candidates=candidates)
            res.metadata["provider"] = "jev_error_fallback"
            res.reasons.insert(0, f"[Jev Warning] Fallback activated ({type(e).__name__}: {e})")
            return res
