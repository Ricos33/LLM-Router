import pytest
from app.router.engine import RouterEngine
from app.models import ChatCompletionRequest, ChatMessage
from app.config import settings
from unittest.mock import patch, AsyncMock
import asyncio

@pytest.mark.asyncio
async def test_auto_truncate_context():
    engine = RouterEngine()
    
    # 50,000 chars ~ 12,500 tokens
    long_msg = ChatMessage(role="user", content="a" * 50000)
    
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[long_msg] * 12  # ~150,000 tokens total
    )
    
    # We will mock decide_route to return a Mistral Small 4 candidate (context length 128,000)
    from app.classifier import ClassificationResult, ModelTier
    from app.router.engine import RoutingDecision
    from app.backends import BaseBackend
    
    class DummyBackend(BaseBackend):
        async def complete(self, request, *args, **kwargs):
            # Record what was sent
            self.last_request = request
            from app.models import ChatCompletionResponse, ChatCompletionChoice, CompletionUsage
            return ChatCompletionResponse(
                model="mistral/mistral-small-4",
                choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content="test"))],
                usage=CompletionUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
            )

    dummy_backend = DummyBackend()
    
    decision = RoutingDecision(
        tier=ModelTier.CHEAP,
        provider_name="mistral",
        model_name="mistral/mistral-small-4",  # context_length=128000
        backend=dummy_backend,
        classifier_score=0.9,
        reasons=[]
    )
    
    settings.auto_truncate_context = True
    settings.gateway_cache_enabled = False # Bypass cache
    
    with patch.object(engine, 'decide_route', return_value=decision):
        resp = await engine.route_and_execute(req)
        
        # Verify the backend received a truncated request
        sent_req = dummy_backend.last_request
        # Expected max tokens ~ 128,000 - 1000 = 127,000 tokens
        # 127,000 * 4 = 508,000 chars. 508,000 / 50,000 = 10.16 messages. So 10 messages should be kept.
        assert len(sent_req.messages) == 10
        assert len(req.messages) == 12 # original intact
