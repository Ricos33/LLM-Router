from abc import ABC, abstractmethod
from typing import Optional
from app.models import ChatCompletionRequest, ChatCompletionResponse


class BaseBackend(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    async def complete(
        self, request: ChatCompletionRequest, model_override: Optional[str] = None, api_key_override: Optional[str] = None
    ) -> ChatCompletionResponse:
        pass
