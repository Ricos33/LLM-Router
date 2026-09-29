import time
import uuid
import logging
from typing import Optional
import httpx
from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessage,
    CompletionUsage,
)
from .base import BaseBackend

logger = logging.getLogger(__name__)


class OllamaBackend(BaseBackend):
    """
    Cheap / Local backend connecting to Ollama's OpenAI-compatible or native API.
    Provides graceful simulation when Ollama daemon is offline and fallback is enabled.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        default_model: str = "llama3.2:3b",
        simulate_fallback: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.simulate_fallback = simulate_fallback

    async def complete(
        self, request: ChatCompletionRequest, model_override: Optional[str] = None, api_key_override: Optional[str] = None, timeout_override: Optional[float] = None
    ) -> ChatCompletionResponse:
        model = model_override or self.default_model
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens

        try:
            timeout_val = timeout_override if timeout_override is not None else 30.0
            async with httpx.AsyncClient(timeout=timeout_val) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

                choice = data["choices"][0]
                usage_data = data.get("usage", {})
                return ChatCompletionResponse(
                    id=data.get("id", f"ollama-{uuid.uuid4().hex[:10]}"),
                    model=model,
                    choices=[
                        ChatCompletionChoice(
                            index=0,
                            message=ChatMessage(
                                role=choice["message"]["role"],
                                content=choice["message"]["content"],
                            ),
                            finish_reason=choice.get("finish_reason", "stop"),
                        )
                    ],
                    usage=CompletionUsage(
                        prompt_tokens=usage_data.get("prompt_tokens", 50),
                        completion_tokens=usage_data.get("completion_tokens", 80),
                        total_tokens=usage_data.get("total_tokens", 130),
                    ),
                )
        except Exception as e:
            if not self.simulate_fallback:
                raise RuntimeError(f"Ollama backend error at {self.base_url}: {e}")

            logger.info(f"Ollama unreachable ({e}); falling back to local simulation.")
            return self._simulated_response(request, model)

    def _simulated_response(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        user_query = request.messages[-1].content if request.messages else ""
        content = (
            f"[Simulated response via {model} (Cheap Backend)]\n"
            f"Processed locally with low-latency inference for query: \"{user_query[:60]}...\""
        )
        prompt_tokens = max(10, len(user_query) // 4)
        completion_tokens = max(20, len(content) // 4)
        return ChatCompletionResponse(
            id=f"ollama-sim-{uuid.uuid4().hex[:8]}",
            model=model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
