import logging
from typing import List, Optional
import httpx
from app.models import ChatMessage
from .base import BaseClassifier
from .types import ClassificationResult, ModelTier
from .rule_based import RuleBasedClassifier

logger = logging.getLogger(__name__)


class JevClassifier(BaseClassifier):
    """
    TypeSafe AI 'Jev' classifier adapter.
    When API credentials are configured, routes classification requests to the Jev service.
    Gracefully falls back to RuleBasedClassifier if credentials are unset or remote service is unreachable.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.typesafe.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.fallback = RuleBasedClassifier()

    def classify(self, messages: List[ChatMessage]) -> ClassificationResult:
        if not self.api_key:
            # TypeSafe AI Jev access pending -> fallback to explainable mock
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_mock_fallback"
            res.reasons.insert(0, "[Jev Pending Access] Evaluated via heuristic classifier")
            return res

        # Synchronous HTTP call for Jev API
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    f"{self.base_url}/classify",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"messages": [m.model_dump() for m in messages]}
                )
                resp.raise_for_status()
                data = resp.json()
                return ClassificationResult(
                    tier=ModelTier(data.get("tier", "cheap")),
                    confidence=float(data.get("confidence", 0.9)),
                    score=float(data.get("score", 0.5)),
                    reasons=data.get("reasons", ["Classified by TypeSafe AI Jev"]),
                    suggested_model=data.get("suggested_model"),
                    metadata={"provider": "typesafe_jev"}
                )
        except Exception as e:
            logger.warning(f"Jev API unreachable, using rule-based fallback: {e}")
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_error_fallback"
            res.reasons.insert(0, f"[Jev Warning] Fallback activated ({type(e).__name__})")
            return res

    async def classify_async(self, messages: List[ChatMessage]) -> ClassificationResult:
        if not self.api_key:
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_mock_fallback"
            res.reasons.insert(0, "[Jev Pending Access] Evaluated via heuristic classifier")
            return res

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
                    f"{self.base_url}/classify",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"messages": [m.model_dump() for m in messages]}
                )
                resp.raise_for_status()
                data = resp.json()
                return ClassificationResult(
                    tier=ModelTier(data.get("tier", "cheap")),
                    confidence=float(data.get("confidence", 0.9)),
                    score=float(data.get("score", 0.5)),
                    reasons=data.get("reasons", ["Classified by TypeSafe AI Jev"]),
                    suggested_model=data.get("suggested_model"),
                    metadata={"provider": "typesafe_jev"}
                )
        except Exception as e:
            logger.warning(f"Async Jev API error, using rule-based fallback: {e}")
            res = self.fallback.classify(messages)
            res.metadata["provider"] = "jev_error_fallback"
            res.reasons.insert(0, f"[Jev Warning] Fallback activated ({type(e).__name__})")
            return res
