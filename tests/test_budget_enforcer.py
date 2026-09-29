import pytest
from app.router.engine import RouterEngine
from app.models import ChatCompletionRequest, ChatMessage
from app.config import settings
from unittest.mock import patch

@pytest.mark.asyncio
async def test_request_budget_enforcer():
    engine = RouterEngine()
    
    # 50,000 chars ~ 12,500 tokens. A frontier model at $10/M tokens = $0.125
    long_msg = ChatMessage(role="user", content="a" * 50000)
    
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[long_msg]
    )
    
    # Mock decide_route
    from app.classifier import ClassificationResult, ModelTier
    from app.router.engine import RoutingDecision
    from app.backends import BaseBackend
    
    class DummyBackend(BaseBackend):
        async def complete(self, request, *args, **kwargs):
            from app.models import ChatCompletionResponse, ChatCompletionChoice, CompletionUsage
            return ChatCompletionResponse(
                model="openai/gpt-6-astra",
                choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content="test"))],
                usage=CompletionUsage(prompt_tokens=12500, completion_tokens=10, total_tokens=12510)
            )
            
    dummy_backend = DummyBackend()

    # Initial decision is FRONTIER
    decision_frontier = RoutingDecision(
        tier=ModelTier.FRONTIER,
        provider_name="openai",
        model_name="openai/gpt-6-astra",  # Price is 10.0 / M
        backend=dummy_backend,
        classifier_score=0.95,
        reasons=["High complexity"]
    )
    
    decision_medium = RoutingDecision(
        tier=ModelTier.MEDIUM,
        provider_name="openai",
        model_name="openai/gpt-5.6-terra",
        backend=dummy_backend,
        classifier_score=0.95,
        reasons=["Downgraded"]
    )
    
    settings.max_cost_per_request_usd = 0.10 # Max 10 cents
    settings.gateway_cache_enabled = False
    
    # decide_route will be called twice if it downgrades
    with patch.object(engine, 'decide_route', side_effect=[decision_frontier, decision_medium]):
        resp = await engine.route_and_execute(req)
        
        # It should have downgraded to medium
        assert resp.router_metadata.routed_tier == "medium"
        assert resp.router_metadata.actual_model == "openai/gpt-5.6-terra"
        assert any("Auto-downgraded from Frontier" in r for r in resp.router_metadata.classifier_reasons)
        
    # Reset
    settings.max_cost_per_request_usd = 0.0
