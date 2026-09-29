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

class AnthropicBackend(BaseBackend):
    def __init__(
        self,
        api_key: str = "",
        default_model: str = "claude-3-opus-20240229",
        simulate_fallback: bool = True,
    ):
        self.api_key = api_key
        self.default_model = default_model
        self.simulate_fallback = simulate_fallback

    async def complete(
        self, request: ChatCompletionRequest, model_override: Optional[str] = None, api_key_override: Optional[str] = None
    ) -> ChatCompletionResponse:
        model = model_override or self.default_model
        
        api_key = api_key_override or self.api_key
        if not api_key and self.simulate_fallback:
            return self._simulated_response(request, model)
            
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        # Extract system messages
        system_content = ""
        anthropic_messages = []
        for msg in request.messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": model,
            "max_tokens": request.max_tokens or 4096,
            "messages": anthropic_messages,
            "stream": False,
        }
        if system_content:
            payload["system"] = system_content.strip()
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

                content = "".join(block["text"] for block in data.get("content", []) if block.get("type") == "text")
                usage = data.get("usage", {})
                return ChatCompletionResponse(
                    id=data.get("id", f"msg-{uuid.uuid4().hex[:10]}"),
                    model=model,
                    choices=[
                        ChatCompletionChoice(
                            index=0,
                            message=ChatMessage(role="assistant", content=content),
                            finish_reason="stop",
                        )
                    ],
                    usage=CompletionUsage(
                        prompt_tokens=usage.get("input_tokens", 80),
                        completion_tokens=usage.get("output_tokens", 220),
                        total_tokens=usage.get("input_tokens", 80) + usage.get("output_tokens", 220),
                    ),
                )
        except Exception as e:
            if not self.simulate_fallback:
                raise RuntimeError(f"Anthropic backend error: {e}")
            logger.info(f"Anthropic error ({e}); falling back to simulated response.")
            return self._simulated_response(request, model)

    def _simulated_response(
        self, request: ChatCompletionRequest, model: str
    ) -> ChatCompletionResponse:
        user_query = request.messages[-1].content if request.messages else ""
        content = (
            f"[Simulated response via {model} (Anthropic Backend)]\n"
            f"Delivering high-depth reasoning and precision "
            f"for prompt: \"{user_query[:60]}...\""
        )
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
            usage=CompletionUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150),
        )
