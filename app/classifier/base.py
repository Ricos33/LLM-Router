from abc import ABC, abstractmethod
from typing import List
from app.models import ChatMessage
from .types import ClassificationResult


class BaseClassifier(ABC):
    """Abstract base classifier interface for LLM routing."""

    @abstractmethod
    def classify(self, messages: List[ChatMessage], strategy: str = "balanced") -> ClassificationResult:
        """Synchronously classify conversation messages."""
        pass

    async def classify_async(self, messages: List[ChatMessage], strategy: str = "balanced") -> ClassificationResult:
        """Asynchronously classify conversation messages (default delegates to sync)."""
        return self.classify(messages, strategy=strategy)
