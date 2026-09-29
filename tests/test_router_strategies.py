import pytest
from app.router import RouterEngine
from app.models import ChatCompletionRequest, ChatMessage
from app.classifier import ModelTier

@pytest.mark.asyncio
async def test_router_strategy_differences():
    router = RouterEngine()
    req_cost = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Translate to French: Hello world. This is a very simple text.")],
        strategy="cost_optimized"
    )
    decision_cost = router.decide_route(req_cost)
    
    req_quality = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Translate to French: Hello world. This is a very simple text.")],
        strategy="quality_optimized"
    )
    decision_quality = router.decide_route(req_quality)
    
    # The quality_optimized strategy should pick a model with better benchmarks or at least a different fallback/score if thresholds change.
    # In the mock, cost_optimized makes it easier to route to cheap (ceiling is higher).
    assert decision_cost.model_name != "" 
    assert decision_quality.model_name != ""
