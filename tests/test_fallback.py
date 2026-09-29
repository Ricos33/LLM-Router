import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.router.engine import RouterEngine
from app.models import ChatCompletionRequest, ChatMessage
from app.classifier.types import ModelTier

@pytest.mark.asyncio
async def test_fallback_with_backoff_and_jitter():
    engine = RouterEngine()
    
    # Create request
    request = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="Hello test")]
    )
    
    # Mock router engine methods
    mock_decision = MagicMock()
    mock_decision.model_name = "model-A"
    mock_decision.provider_name = "prov-A"
    mock_decision.tier = ModelTier.FRONTIER
    mock_decision.classifier_score = 0.9
    mock_decision.reasons = []
    mock_decision.matched_rule = None
    
    mock_backend_A = MagicMock()
    mock_backend_A.complete = AsyncMock(side_effect=Exception("Timeout or fail"))
    mock_decision.backend = mock_backend_A
    
    mock_fallback_1 = MagicMock()
    mock_fallback_1.model_name = "model-B"
    mock_fallback_1.provider_name = "prov-B"
    mock_fallback_1.tier = ModelTier.FRONTIER
    mock_fallback_1.classifier_score = 0.8
    mock_fallback_1.reasons = []
    mock_fallback_1.matched_rule = None
    mock_backend_B = MagicMock()
    
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    
    mock_backend_B.complete = AsyncMock(return_value=mock_response)
    mock_fallback_1.backend = mock_backend_B
    
    # We patch decide_route and get_fallback_candidates
    with patch.object(engine, "decide_route", return_value=mock_decision), \
         patch.object(engine, "get_fallback_candidates", return_value=[mock_fallback_1]), \
         patch("app.router.engine.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
             
        completion = await engine.route_and_execute(request)
        
        # Verify first was called and failed
        assert mock_backend_A.complete.call_count == 1
        
        # Verify sleep was called (backoff)
        assert mock_sleep.call_count == 1
        args, _ = mock_sleep.call_args
        sleep_time = args[0]
        assert 1.0 <= sleep_time < 2.0 # idx 0, 2**0 = 1 + jitter (0-1)
        
        # Verify second was called and succeeded
        assert mock_backend_B.complete.call_count == 1
        
        # Verify fallback metadata
        assert completion.router_metadata.fallback_triggered is True
        assert len(completion.router_metadata.fallback_chain) == 2
        assert "model-A (failed: Timeout or fail)" in completion.router_metadata.fallback_chain[0]
        assert "model-B (succeeded)" in completion.router_metadata.fallback_chain[1]
