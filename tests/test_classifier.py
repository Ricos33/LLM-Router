import pytest
from app.classifier import RuleBasedClassifier, JevClassifier, ModelTier
from app.models import ChatMessage


def test_classifier_cheap_intent():
    classifier = RuleBasedClassifier(threshold=0.50)
    messages = [ChatMessage(role="user", content="Hello, how are you?")]
    result = classifier.classify(messages)

    assert result.tier == ModelTier.CHEAP
    assert result.score < 0.50
    assert len(result.reasons) > 0


def test_classifier_code_intent():
    classifier = RuleBasedClassifier(threshold=0.50)
    messages = [
        ChatMessage(
            role="user",
            content="def calculate_fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)",
        )
    ]
    result = classifier.classify(messages)

    assert result.tier == ModelTier.FRONTIER
    assert result.score >= 0.50
    assert any("programming" in r.lower() or "code" in r.lower() for r in result.reasons)


def test_classifier_reasoning_intent():
    classifier = RuleBasedClassifier(threshold=0.50)
    messages = [
        ChatMessage(
            role="user",
            content="Can you derive the mathematical proof for the asymptotic complexity of this distributed consensus architecture?",
        )
    ]
    result = classifier.classify(messages)

    assert result.tier == ModelTier.FRONTIER
    assert result.score >= 0.50


def test_classifier_empty_context():
    classifier = RuleBasedClassifier()
    result = classifier.classify([])
    assert result.tier == ModelTier.CHEAP


def test_jev_classifier_fallback_without_key():
    jev = JevClassifier(api_key=None)
    messages = [ChatMessage(role="user", content="Hi there")]
    result = jev.classify(messages)

    assert result.tier == ModelTier.CHEAP
    assert "jev_mock_fallback" in result.metadata.get("provider", "")
