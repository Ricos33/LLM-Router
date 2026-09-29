from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app.models import ChatMessage
from .types import ClassificationResult


class BaseClassifier(ABC):
    """Abstract base classifier interface for LLM routing."""

    @abstractmethod
    def classify(
        self,
        messages: List[ChatMessage],
        strategy: str = "balanced",
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> ClassificationResult:
        """Synchronously classify conversation messages.

        `candidates` is an optional shortlist of catalog model dicts
        (id, name, provider, tier, pricing, context_length, scores).
        Classifiers that can do per-model evaluation (e.g. Jev) use it
        to tailor their questions; others may ignore it.
        """
        pass

    async def classify_async(
        self,
        messages: List[ChatMessage],
        strategy: str = "balanced",
        candidates: Optional[List[Dict[str, Any]]] = None,
    ) -> ClassificationResult:
        """Asynchronously classify conversation messages (default delegates to sync)."""
        return self.classify(messages, strategy=strategy, candidates=candidates)
