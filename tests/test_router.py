import pytest
from app.router import RouterEngine
from app.models import ChatCompletionRequest, ChatMessage
from app.classifier import ModelTier


@pytest.mark.asyncio
async def test_router_auto_cheap():
    router = RouterEngine()
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="What is the capital of Canada?")]
    )
    decision = router.decide_route(req)
    assert decision.tier == ModelTier.CHEAP

    res = await router.route_and_execute(req)
    assert res.router_metadata is not None
    assert res.router_metadata.routed_tier == "cheap"
    assert res.router_metadata.cost_saved_usd >= 0.0


@pytest.mark.asyncio
async def test_router_header_override_frontier():
    router = RouterEngine()
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Hello")]
    )
    decision = router.decide_route(req, tier_header_override="frontier")
    assert decision.tier == ModelTier.FRONTIER
    assert "override" in decision.reasons[0].lower()


@pytest.mark.asyncio
async def test_router_header_override_cheap():
    router = RouterEngine()
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Write a compiler in C++")]
    )
    decision = router.decide_route(req, tier_header_override="cheap")
    assert decision.tier == ModelTier.CHEAP
    assert "override" in decision.reasons[0].lower()


@pytest.mark.asyncio
async def test_router_model_override():
    router = RouterEngine()
    req = ChatCompletionRequest(
        model="router-frontier",
        messages=[ChatMessage(role="user", content="Hi")]
    )
    decision = router.decide_route(req)
    assert decision.tier == ModelTier.FRONTIER


@pytest.mark.asyncio
async def test_router_header_override_medium():
    router = RouterEngine()
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Translate this text to Spanish")]
    )
    decision = router.decide_route(req, tier_header_override="medium")
    assert decision.tier == ModelTier.MEDIUM


@pytest.mark.asyncio
async def test_router_agy_model_targets():
    router = RouterEngine()

    req_cheap = ChatCompletionRequest(
        model="agy-cheap",
        messages=[ChatMessage(role="user", content="Quick query")]
    )
    dec_cheap = router.decide_route(req_cheap)
    assert dec_cheap.tier == ModelTier.CHEAP
    assert dec_cheap.provider_name == "agy"

    req_med = ChatCompletionRequest(
        model="agy-medium",
        messages=[ChatMessage(role="user", content="Code analysis")]
    )
    dec_med = router.decide_route(req_med)
    assert dec_med.tier == ModelTier.MEDIUM
    assert dec_med.provider_name == "agy"

    req_front = ChatCompletionRequest(
        model="agy-frontier",
        messages=[ChatMessage(role="user", content="Deep theory")]
    )
    dec_front = router.decide_route(req_front)
    assert dec_front.tier == ModelTier.FRONTIER
    assert dec_front.provider_name == "agy"


@pytest.mark.asyncio
async def test_router_jev_wiring_and_execution():
    from unittest.mock import patch, MagicMock
    from app.config import settings
    from app.classifier import JevClassifier
    import httpx

    fake_response = {
        "model": "jev-1.13.0",
        "answers": {
            "tier": {
                "type": "choice",
                "choice": "frontier",
                "confidence": 0.94,
                "probabilities": {"cheap": 0.02, "medium": 0.04, "frontier": 0.94}
            },
            "complexity": {
                "type": "score",
                "score": 1.9,
                "confidence": 0.95
            }
        },
        "usage": {"input_tokens": 100, "output_tokens": 20}
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response
    mock_resp.raise_for_status = MagicMock()

    original_mode = settings.classifier_mode
    original_key = settings.jev_api_key

    try:
        settings.classifier_mode = "jev"
        settings.jev_api_key = "test-jev-key"

        router = RouterEngine()
        assert isinstance(router.classifier, JevClassifier)

        req = ChatCompletionRequest(
            model="router-auto",
            messages=[ChatMessage(role="user", content="Explain quantum entanglement")]
        )

        with patch.object(httpx.Client, "post", return_value=mock_resp):
            decision = router.decide_route(req)
            assert decision.tier == ModelTier.FRONTIER
            assert "typesafe_jev" in decision.reasons[0].lower() or "jev" in decision.reasons[0].lower()

            res = await router.route_and_execute(req)
            assert res.router_metadata.routed_tier == "frontier"
    finally:
        settings.classifier_mode = original_mode
        settings.jev_api_key = original_key


def test_router_jev_fallback_warning_when_key_missing(caplog):
    from app.config import settings
    from app.classifier import JevClassifier

    original_mode = settings.classifier_mode
    original_key = settings.jev_api_key

    try:
        settings.classifier_mode = "jev"
        settings.jev_api_key = ""

        with caplog.at_level("WARNING"):
            router = RouterEngine()

        assert isinstance(router.classifier, JevClassifier)
        assert any("CLASSIFIER_MODE is 'jev' but JEV_API_KEY is not configured" in rec.message for rec in caplog.records)
    finally:
        settings.classifier_mode = original_mode
        settings.jev_api_key = original_key


@pytest.mark.asyncio
async def test_resilient_fallback_chain_on_primary_failure():
    from unittest.mock import AsyncMock
    router = RouterEngine()

    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Hi!")]
    )

    # Mock cheap backend to fail on first attempt
    original_complete = router.cheap_backend.complete
    call_count = 0

    async def mock_fail_then_succeed(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("503 Service Unavailable on primary model")
        return await original_complete(*args, **kwargs)

    router.cheap_backend.complete = mock_fail_then_succeed

    try:
        res = await router.route_and_execute(req)
        assert res.router_metadata is not None
        assert res.router_metadata.fallback_triggered is True
        assert len(res.router_metadata.fallback_chain) >= 2
        assert any("failed" in step for step in res.router_metadata.fallback_chain)
        assert any("succeeded" in step for step in res.router_metadata.fallback_chain)
    finally:
        router.cheap_backend.complete = original_complete


def test_provider_circuit_breaker():
    from app.router.circuit_breaker import ProviderCircuitBreaker

    cb = ProviderCircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
    provider = "anthropic"

    # Initially healthy
    assert cb.is_available(provider) is True

    # 1 failure -> degraded but still available
    cb.record_failure(provider, "500 Internal Error")
    assert cb.is_available(provider) is True
    status = cb.get_health_status()
    assert status[provider]["status"] == "degraded"
    assert status[provider]["consecutive_failures"] == 1

    # 2nd failure
    cb.record_failure(provider, "502 Bad Gateway")
    assert cb.is_available(provider) is True

    # 3rd failure -> tripped
    cb.record_failure(provider, "504 Gateway Timeout")
    assert cb.is_available(provider) is False
    status = cb.get_health_status()
    assert status[provider]["status"] == "tripped"
    assert status[provider]["consecutive_failures"] == 3

    # Wait for cooldown to expire
    import time
    time.sleep(0.15)
    # Should now be available (half-open)
    assert cb.is_available(provider) is True

    # Successful recovery resets count
    cb.record_success(provider)
    status = cb.get_health_status()
    assert status[provider]["status"] == "healthy"
    assert status[provider]["consecutive_failures"] == 0



