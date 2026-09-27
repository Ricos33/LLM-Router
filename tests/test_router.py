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


