import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.router.engine import RouterEngine
from app.models import ChatCompletionRequest, ChatMessage
from app.classifier.types import ModelTier
from app.config import settings

@pytest.mark.asyncio
async def test_timeouts_configurable_per_tier():
    engine = RouterEngine()
    
    # We will patch get_model_by_id so we don't need real models in catalog
    request = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="Test timeout")]
    )
    
    # Setup mock decision
    mock_decision = MagicMock()
    mock_decision.model_name = "model-slow"
    mock_decision.provider_name = "prov-slow"
    mock_decision.tier = ModelTier.CHEAP
    mock_decision.classifier_score = 0.5
    mock_decision.reasons = []
    mock_decision.matched_rule = None
    
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 10
    
    mock_backend = MagicMock()
    mock_backend.complete = AsyncMock(return_value=mock_response)
    mock_decision.backend = mock_backend
    
    settings.cheap_timeout_seconds = 4.2
    
    with patch.object(engine, "decide_route", return_value=mock_decision), \
         patch.object(engine, "get_fallback_candidates", return_value=[]):
             
        await engine.route_and_execute(request)
        
        # Verify the backend was called with the configured cheap timeout
        assert mock_backend.complete.call_count == 1
        call_kwargs = mock_backend.complete.call_args[1]
        assert call_kwargs.get("timeout_override") == 4.2
