import os
import time
import uuid
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple, List

from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessage,
    CompletionUsage,
    RouterMetadata,
)
from .base import BaseBackend

logger = logging.getLogger(__name__)

DEFAULT_AGY_TIER_MAP: Dict[str, Dict[str, Any]] = {
    "cheap": {
        "model": "gemini-3.8-flash-low",
        "effort": "low",
    },
    "medium": {
        "model": "gemini-3.1-pro-high",
        "effort": "high",
    },
    "frontier": {
        "model": "claude-opus-4-6-thinking",
        "effort": None,
    },
}


class AgyBackend(BaseBackend):
    """
    Backend routing requests to the local Antigravity CLI ('agy') in headless mode.
    Executes 'agy -p "<prompt>" --model <model> [--effort <effort>]'.
    """

    def __init__(
        self,
        binary_path: str = "~/workspace/cli-tools/bin/agy",
        tier_map: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0,
        simulate_fallback: bool = True,
        default_tier: str = "cheap",
    ):
        self.binary_path = binary_path
        self.timeout = timeout
        self.simulate_fallback = simulate_fallback
        self.default_tier = default_tier.lower()
        self.tier_map = self._normalize_tier_map(tier_map or DEFAULT_AGY_TIER_MAP)

    def _normalize_tier_map(self, raw_map: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        normalized: Dict[str, Dict[str, Any]] = {}
        for tier, val in raw_map.items():
            tier_key = str(tier).strip().lower()
            if isinstance(val, dict):
                normalized[tier_key] = {
                    "model": val.get("model", "gemini-3.8-flash-low"),
                    "effort": val.get("effort"),
                }
            elif isinstance(val, str):
                normalized[tier_key] = {
                    "model": val,
                    "effort": None,
                }
            else:
                normalized[tier_key] = {
                    "model": str(val),
                    "effort": None,
                }
        return normalized

    def get_tier_config(self, tier: str) -> Dict[str, Any]:
        tier_key = tier.lower().strip()
        if tier_key in self.tier_map:
            return self.tier_map[tier_key]
        if self.default_tier in self.tier_map:
            return self.tier_map[self.default_tier]
        return {"model": "gemini-3.8-flash-low", "effort": "low"}

    def get_model_for_tier(self, tier: str) -> str:
        return self.get_tier_config(tier).get("model", "gemini-3.8-flash-low")

    def get_tier_for_model(self, model: str) -> Optional[str]:
        target = model.strip().lower()
        for tier, conf in self.tier_map.items():
            if conf.get("model", "").lower() == target:
                return tier
        return None

    def resolve_target(
        self, model_override: Optional[str] = None, api_key_override: Optional[str] = None, request_model: Optional[str] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Resolve (tier, model, effort) from override or request model.
        """
        candidate = (model_override or "").strip().lower()
        req = (request_model or "").strip().lower()

        # 1. Direct tier name in override
        if candidate in self.tier_map:
            conf = self.tier_map[candidate]
            return candidate, conf["model"], conf.get("effort")

        # 2. Candidate matches a known configured model
        tier_from_cand = self.get_tier_for_model(candidate)
        if tier_from_cand:
            conf = self.tier_map[tier_from_cand]
            return tier_from_cand, candidate, conf.get("effort")

        # 3. Model name in request indicates tier
        for t in ("frontier", "medium", "cheap"):
            if t in req or f"agy-{t}" in req or f"router-{t}" in req:
                conf = self.tier_map.get(t, self.get_tier_config(t))
                return t, conf["model"], conf.get("effort")

        # 4. Request matches a known configured model
        tier_from_req = self.get_tier_for_model(req)
        if tier_from_req:
            conf = self.tier_map[tier_from_req]
            return tier_from_req, req, conf.get("effort")

        # 5. Candidate is an explicit unmapped model name
        if candidate and candidate not in ("router-auto", "auto", "default"):
            return "custom", candidate, None

        # 6. Fallback to default tier
        default_conf = self.get_tier_config(self.default_tier)
        return self.default_tier, default_conf["model"], default_conf.get("effort")

    def format_prompt(self, messages: List[ChatMessage]) -> str:
        if not messages:
            return ""
        if len(messages) == 1 and messages[0].role in ("user", ""):
            return messages[0].content

        lines = []
        for msg in messages:
            role = msg.role.capitalize() if msg.role else "User"
            lines.append(f"{role}: {msg.content}")
        return "\n\n".join(lines)

    def build_command(
        self, prompt: str, model: str, effort: Optional[str] = None
    ) -> List[str]:
        expanded_bin = os.path.expanduser(self.binary_path)
        cmd = [expanded_bin, "-p", prompt, "--model", model]

        # Support reasoning effort if provided and model does not reject --effort (e.g. claude-*)
        if effort and not model.lower().startswith("claude-"):
            effort_str = str(effort).strip().lower()
            if effort_str in ("low", "medium", "high", "max"):
                cmd.extend(["--effort", effort_str])

        cmd.extend(["--output-format", "text"])
        return cmd

    async def complete(
        self, request: ChatCompletionRequest, model_override: Optional[str] = None, api_key_override: Optional[str] = None, timeout_override: Optional[float] = None
    ) -> ChatCompletionResponse:
        tier, target_model, effort = self.resolve_target(
            model_override=model_override, request_model=request.model
        )
        prompt = self.format_prompt(request.messages)
        start_time = time.perf_counter()

        expanded_bin = os.path.expanduser(self.binary_path)
        if not os.path.exists(expanded_bin):
            if self.simulate_fallback:
                logger.warning(
                    f"Agy binary not found at '{expanded_bin}'; falling back to simulation."
                )
                return self._simulated_response(request, target_model, tier)
            raise FileNotFoundError(f"Agy binary not found at '{expanded_bin}'")

        cmd = self.build_command(prompt=prompt, model=target_model, effort=effort)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                timeout_val = timeout_override if timeout_override is not None else self.timeout
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_val
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                if self.simulate_fallback:
                    logger.warning(
                        f"Agy CLI timed out after {timeout_val}s; falling back to simulation."
                    )
                    return self._simulated_response(
                        request,
                        target_model,
                        tier,
                        latency_ms=round(self.timeout * 1000.0, 2),
                    )
                raise TimeoutError(f"Agy CLI process timed out after {self.timeout}s")

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                if self.simulate_fallback:
                    logger.warning(
                        f"Agy CLI failed (code {proc.returncode}: {err_msg}); falling back to simulation."
                    )
                    return self._simulated_response(request, target_model, tier)
                raise RuntimeError(
                    f"Agy CLI execution failed (exit code {proc.returncode}): {err_msg}"
                )

            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            output_text = stdout.decode("utf-8", errors="replace").strip()

            prompt_tokens = max(1, len(prompt) // 4)
            completion_tokens = max(1, len(output_text) // 4)

            score = 1.0 if tier == "frontier" else 0.5 if tier == "medium" else 0.0
            reasons = [
                f"Executed via local Agy CLI backend ({tier} tier, model: {target_model})"
            ]
            if effort:
                reasons.append(f"Reasoning effort: {effort}")

            response = ChatCompletionResponse(
                id=f"agy-{uuid.uuid4().hex[:10]}",
                model=target_model,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=output_text),
                        finish_reason="stop",
                    )
                ],
                usage=CompletionUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
            response.router_metadata = RouterMetadata(
                routed_tier=tier,
                classifier_score=score,
                classifier_reasons=reasons,
                actual_model=target_model,
                upstream_provider="agy",
                latency_ms=latency_ms,
                cost_actual_usd=0.0,
                cost_frontier_usd=0.0,
                cost_saved_usd=0.0,
            )
            return response

        except (TimeoutError, RuntimeError, FileNotFoundError):
            raise
        except Exception as e:
            if self.simulate_fallback:
                logger.warning(
                    f"Unexpected error executing Agy CLI ({e}); falling back to simulation."
                )
                return self._simulated_response(request, target_model, tier)
            raise RuntimeError(f"Unexpected error running Agy backend: {e}")

    def _simulated_response(
        self,
        request: ChatCompletionRequest,
        model: str,
        tier: str,
        latency_ms: float = 15.0,
    ) -> ChatCompletionResponse:
        user_query = request.messages[-1].content if request.messages else ""
        content = (
            f"[Simulated response via Agy CLI ({model} - {tier.upper()} Tier)]\n"
            f"Headless inference completed for prompt: \"{user_query[:60]}...\""
        )
        prompt_tokens = max(10, len(user_query) // 4)
        completion_tokens = max(20, len(content) // 4)

        score = 1.0 if tier == "frontier" else 0.5 if tier == "medium" else 0.0
        response = ChatCompletionResponse(
            id=f"agy-sim-{uuid.uuid4().hex[:8]}",
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
        response.router_metadata = RouterMetadata(
            routed_tier=tier,
            classifier_score=score,
            classifier_reasons=[
                f"Simulated Agy fallback ({tier} tier, model: {model})"
            ],
            actual_model=model,
            upstream_provider="agy",
            latency_ms=latency_ms,
            cost_actual_usd=0.0,
            cost_frontier_usd=0.0,
            cost_saved_usd=0.0,
        )
        return response
