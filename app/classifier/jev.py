import logging
from typing import List, Optional, Dict, Any
import httpx
from app.models import ChatMessage
from .base import BaseClassifier
from .types import ClassificationResult, ModelTier
from .rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)

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

    def _build_payload(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        return {
            "model": self.model,
            "state": {
                "messages": [m.model_dump() for m in messages]
            },
            "questions": {
                "tier": {
                    "type": "choice",
                    "instructions": "Determine the optimal LLM model tier (cheap, medium, or frontier) to handle this conversation/request based on complexity, reasoning depth, and technical requirements.",
                    "criteria": {
                        "cheap": "Simple, routine queries, greetings, basic facts, straightforward translations or summaries.",
                        "medium": "Moderate complexity, intermediate tasks, multi-step instructions, standard code snippets.",
                        "frontier": "Complex reasoning, advanced coding, system architecture, mathematical proofs, deep technical troubleshooting."
                    }
                },
                "complexity": {
                    "type": "score",
                    "instructions": "Rate the overall technical and reasoning complexity of the request.",
                    "criteria": [
                        "Low complexity: routine or simple query",
                        "Moderate complexity: intermediate tasks",
                        "High complexity: intricate reasoning or advanced problem-solving"
                    ]
                }
            }
        }

    def _parse_response(self, data: Dict[str, Any]) -> ClassificationResult:
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
            if "probabilities" in tier_answer and isinstance(tier_answer["probabilities"], dict):
                probs_str = ", ".join(f"{k}: {v:.2f}" for k, v in tier_answer["probabilities"].items())
                reasons.append(f"Jev tier probabilities: {probs_str}")
            if raw_score is not None:
                reasons.append(f"Jev complexity score: {float(raw_score):.2f}")

            return ClassificationResult(
                tier=tier,
                confidence=round(confidence, 2),
                score=round(score, 3),
                reasons=reasons,
                suggested_model=tier.value,
                metadata={
                    "provider": "typesafe_jev",
                    "model": data.get("model", self.model),
                    "usage": data.get("usage", {})
                }
            )

        # 2. Legacy / simplified response fallback
        raw_tier = str(data.get("tier", "cheap")).lower().strip()
        tier = TIER_MAPPING.get(raw_tier, ModelTier.CHEAP)
        return ClassificationResult(
            tier=tier,
            confidence=float(data.get("confidence", 0.90)),
            score=float(data.get("score", 0.50)),
            reasons=data.get("reasons", [f"Classified by TypeSafe AI Jev ({tier.value})"]),
            suggested_model=data.get("suggested_model", tier.value),
            metadata={
                "provider": "typesafe_jev",
                "model": data.get("model", self.model),
                "usage": data.get("usage", {})
            }
        )

    def classify(self, messages: List[ChatMessage]) -> ClassificationResult:
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
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_mock_fallback"
            res.reasons.insert(0, "[Jev Fallback] JEV_API_KEY not configured; evaluated via rule-based classifier")
            return res

        url = self._get_endpoint_url()
        payload = self._build_payload(messages)

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
                return self._parse_response(data)
        except Exception as e:
            logger.warning("Jev API request failed (%s: %s). Falling back to rule-based mock classifier.", type(e).__name__, e)
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_error_fallback"
            res.reasons.insert(0, f"[Jev Warning] Fallback activated ({type(e).__name__}: {e})")
            return res

    async def classify_async(self, messages: List[ChatMessage]) -> ClassificationResult:
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
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_mock_fallback"
            res.reasons.insert(0, "[Jev Fallback] JEV_API_KEY not configured; evaluated via rule-based classifier")
            return res

        url = self._get_endpoint_url()
        payload = self._build_payload(messages)

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
                return self._parse_response(data)
        except Exception as e:
            logger.warning("Async Jev API request failed (%s: %s). Falling back to rule-based mock classifier.", type(e).__name__, e)
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_error_fallback"
            res.reasons.insert(0, f"[Jev Warning] Fallback activated ({type(e).__name__}: {e})")
            return res
