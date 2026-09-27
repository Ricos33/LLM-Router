import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from app.backends import AgyBackend, DEFAULT_AGY_TIER_MAP
from app.models import ChatCompletionRequest, ChatMessage
from app.router import RouterEngine
from app.classifier import ModelTier
from app.config import settings


def test_agy_backend_command_builder():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        tier_map=DEFAULT_AGY_TIER_MAP,
    )

    # Cheap: gemini-3.8-flash-low with effort low
    cmd_cheap = backend.build_command("Hello", "gemini-3.8-flash-low", effort="low")
    assert "/test/bin/agy" in cmd_cheap[0]
    assert "-p" in cmd_cheap
    assert "Hello" in cmd_cheap
    assert "--model" in cmd_cheap
    assert "gemini-3.8-flash-low" in cmd_cheap
    assert "--effort" in cmd_cheap
    assert "low" in cmd_cheap
    assert "--output-format" in cmd_cheap
    assert "text" in cmd_cheap

    # Medium: gemini-3.1-pro-high with effort high
    cmd_med = backend.build_command("Solve", "gemini-3.1-pro-high", effort="high")
    assert "gemini-3.1-pro-high" in cmd_med
    assert "--effort" in cmd_med
    assert "high" in cmd_med

    # Frontier: claude-opus-4-6-thinking (claude rejects --effort)
    cmd_frontier = backend.build_command("Complex", "claude-opus-4-6-thinking", effort=None)
    assert "claude-opus-4-6-thinking" in cmd_frontier
    assert "--effort" not in cmd_frontier

    # Claude model with explicit effort should still not include --effort
    cmd_claude_effort = backend.build_command("Complex", "claude-sonnet-4-6", effort="high")
    assert "--effort" not in cmd_claude_effort


@pytest.mark.asyncio
async def test_agy_backend_complete_cheap_mocked():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        tier_map=DEFAULT_AGY_TIER_MAP,
        simulate_fallback=False,
    )
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Hi there")]
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"Flash output response", b""))
    mock_proc.returncode = 0

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)) as mock_exec:
        res = await backend.complete(req, model_override="cheap")

        assert mock_exec.called
        call_args = mock_exec.call_args[0]
        assert "--model" in call_args
        assert "gemini-3.8-flash-low" in call_args
        assert "--effort" in call_args
        assert "low" in call_args

        assert res.choices[0].message.content == "Flash output response"
        assert res.model == "gemini-3.8-flash-low"
        assert res.router_metadata is not None
        assert res.router_metadata.routed_tier == "cheap"
        assert res.router_metadata.actual_model == "gemini-3.8-flash-low"
        assert res.router_metadata.upstream_provider == "agy"
        assert res.router_metadata.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_agy_backend_complete_medium_mocked():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        tier_map=DEFAULT_AGY_TIER_MAP,
        simulate_fallback=False,
    )
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Medium complexity query")]
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"Pro output response", b""))
    mock_proc.returncode = 0

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)) as mock_exec:
        res = await backend.complete(req, model_override="medium")

        assert mock_exec.called
        call_args = mock_exec.call_args[0]
        assert "gemini-3.1-pro-high" in call_args
        assert "high" in call_args

        assert res.choices[0].message.content == "Pro output response"
        assert res.model == "gemini-3.1-pro-high"
        assert res.router_metadata.routed_tier == "medium"


@pytest.mark.asyncio
async def test_agy_backend_complete_frontier_mocked():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        tier_map=DEFAULT_AGY_TIER_MAP,
        simulate_fallback=False,
    )
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Frontier reasoning query")]
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"Opus reasoning response", b""))
    mock_proc.returncode = 0

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)) as mock_exec:
        res = await backend.complete(req, model_override="frontier")

        assert mock_exec.called
        call_args = mock_exec.call_args[0]
        assert "claude-opus-4-6-thinking" in call_args
        assert "--effort" not in call_args

        assert res.choices[0].message.content == "Opus reasoning response"
        assert res.model == "claude-opus-4-6-thinking"
        assert res.router_metadata.routed_tier == "frontier"


@pytest.mark.asyncio
async def test_agy_backend_timeout_fallback():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        timeout=0.01,
        simulate_fallback=True,
    )
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Will timeout")]
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_proc.kill = MagicMock()
    mock_proc.wait = AsyncMock()

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        res = await backend.complete(req, model_override="cheap")
        assert res.choices[0].message.content.startswith("[Simulated response via Agy CLI")
        assert res.router_metadata.routed_tier == "cheap"


@pytest.mark.asyncio
async def test_agy_backend_timeout_raises_without_fallback():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        timeout=0.01,
        simulate_fallback=False,
    )
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Will timeout")]
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_proc.kill = MagicMock()
    mock_proc.wait = AsyncMock()

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        with pytest.raises(TimeoutError):
            await backend.complete(req, model_override="cheap")


@pytest.mark.asyncio
async def test_agy_backend_error_code_fallback():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        simulate_fallback=True,
    )
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="CLI error")]
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b"Unknown flag error"))
    mock_proc.returncode = 1

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        res = await backend.complete(req, model_override="medium")
        assert res.choices[0].message.content.startswith("[Simulated response via Agy CLI")
        assert res.router_metadata.routed_tier == "medium"


@pytest.mark.asyncio
async def test_agy_backend_error_code_raises_without_fallback():
    backend = AgyBackend(
        binary_path="/test/bin/agy",
        simulate_fallback=False,
    )
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="CLI error")]
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b"Unknown flag error"))
    mock_proc.returncode = 1

    with patch("os.path.exists", return_value=True), \
         patch("asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)):
        with pytest.raises(RuntimeError):
            await backend.complete(req, model_override="frontier")


@pytest.mark.asyncio
async def test_router_engine_with_agy_enabled():
    mock_backend = MagicMock()
    mock_backend.get_model_for_tier = MagicMock(side_effect=lambda t: f"agy-{t}-model")
    mock_backend.get_tier_for_model = MagicMock(return_value=None)
    mock_backend.complete = AsyncMock(return_value=MagicMock(
        usage=MagicMock(prompt_tokens=10, completion_tokens=20),
        choices=[MagicMock(message=MagicMock(content="Mocked Agy response"))]
    ))

    with patch.object(settings, "agy_enabled", True):
        router = RouterEngine(agy_backend=mock_backend)

        # 1. Simple query -> Agy cheap
        req_cheap = ChatCompletionRequest(
            model="router-auto",
            messages=[ChatMessage(role="user", content="Hi there")]
        )
        dec_cheap = router.decide_route(req_cheap)
        assert dec_cheap.tier == ModelTier.CHEAP
        assert dec_cheap.provider_name == "agy"
        assert dec_cheap.model_name == "agy-cheap-model"

        # 2. Code query -> Agy frontier
        req_code = ChatCompletionRequest(
            model="router-auto",
            messages=[ChatMessage(role="user", content="Can you write a python script to implement distributed consensus algorithm and derive its asymptotic complexity proof?")]
        )
        dec_code = router.decide_route(req_code)
        assert dec_code.tier == ModelTier.FRONTIER
        assert dec_code.provider_name == "agy"
        assert dec_code.model_name == "agy-frontier-model"

        # 3. Header override -> Medium
        req_mid = ChatCompletionRequest(
            model="router-auto",
            messages=[ChatMessage(role="user", content="Explain")]
        )
        dec_mid = router.decide_route(req_mid, tier_header_override="medium")
        assert dec_mid.tier == ModelTier.MEDIUM
        assert dec_mid.provider_name == "agy"
        assert dec_mid.model_name == "agy-medium-model"

        # 4. Model override -> agy-medium
        req_model = ChatCompletionRequest(
            model="agy-medium",
            messages=[ChatMessage(role="user", content="Review")]
        )
        dec_model = router.decide_route(req_model)
        assert dec_model.tier == ModelTier.MEDIUM
        assert dec_model.provider_name == "agy"
