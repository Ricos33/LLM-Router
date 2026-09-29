import pytest
from app.classifier.jev import JevClassifier
from app.models import ChatCompletionRequest, ChatMessage

def test_jev_build_payload():
    classifier = JevClassifier()
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Explain quantum physics")]
    )
    candidates = [
        {
            "id": "anthropic/claude-sonnet-5",
            "provider": "anthropic",
            "tier": "medium",
            "price_in": 2.0,
            "price_out": 10.0,
            "context_length": 200000,
            "scores": {"Reasoning": 0.8, "Coding": 0.7}
        }
    ]
    payload = classifier._build_payload(req.messages, candidates)
    
    assert "questions" in payload
    assert "tier" in payload["questions"]
    assert "complexity" in payload["questions"]
    assert "domain" in payload["questions"]
    
    assert payload["questions"]["domain"]["type"] == "choice"
    assert "complex_reasoning" in payload["questions"]["domain"]["criteria"]
    
    # Test candidate fit question
    assert "fit_anthropic_claude_sonnet_5" in payload["questions"]
    fit_q = payload["questions"]["fit_anthropic_claude_sonnet_5"]
    assert fit_q["type"] == "score"
    assert "2.0" in fit_q["instructions"]
    assert "200 000" in fit_q["instructions"]
    assert "Reasoning: 0.8" in fit_q["instructions"]
