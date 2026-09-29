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


class OpenAICompatibleBackend(BaseBackend):
    """
    Frontier LLM backend calling any OpenAI-compatible API
    (e.g., OpenAI, OpenRouter, Groq, Together, DeepSeek, Anthropic OpenAI-compat).
    """

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        default_model: str = "gpt-4o",
        simulate_fallback: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.simulate_fallback = simulate_fallback

    async def complete(
        self, request: ChatCompletionRequest, model_override: Optional[str] = None, api_key_override: Optional[str] = None, timeout_override: Optional[float] = None
    ) -> ChatCompletionResponse:
        model = model_override or self.default_model
        headers = {
            "Content-Type": "application/json",
        }
        api_key = api_key_override or self.api_key
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.response_format:
            payload["response_format"] = request.response_format

        try:
            # If no API key configured and simulation is enabled, avoid failing network call
            if not api_key and self.simulate_fallback:
                logger.info("Frontier API key not set; serving simulated frontier response.")
                return self._simulated_response(request, model)

            timeout_val = timeout_override if timeout_override is not None else 45.0
            async with httpx.AsyncClient(timeout=timeout_val) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

                choice = data["choices"][0]
                usage_data = data.get("usage", {})
                return ChatCompletionResponse(
                    id=data.get("id", f"frontier-{uuid.uuid4().hex[:10]}"),
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
                        prompt_tokens=usage_data.get("prompt_tokens", 80),
                        completion_tokens=usage_data.get("completion_tokens", 220),
                        total_tokens=usage_data.get("total_tokens", 300),
                    ),
                )
        except Exception as e:
            if not self.simulate_fallback or api_key_override:
                raise RuntimeError(f"Frontier backend error at {self.base_url}: {e}")

            logger.info(f"Frontier error ({e}); falling back to simulated response.")
            return self._simulated_response(request, model)

    def _simulated_response(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        user_query = request.messages[-1].content if request.messages else ""
        content = (
            f"[Simulated response via {model} (Frontier Backend)]\n"
            f"Delivering high-depth reasoning, precise technical output, and comprehensive analysis "
            f"for prompt: \"{user_query[:60]}...\""
        )
        prompt_tokens = max(25, len(user_query) // 4)
        completion_tokens = max(100, len(content) // 4 + 80)
        return ChatCompletionResponse(
            id=f"frontier-sim-{uuid.uuid4().hex[:8]}",
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
