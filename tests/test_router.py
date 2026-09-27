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
