import pytest
from app.classifier import RuleBasedClassifier, JevClassifier, ModelTier
from app.models import ChatMessage


def test_classifier_cheap_intent():
    classifier = RuleBasedClassifier(threshold=0.50)
    messages = [ChatMessage(role="user", content="Hello, how are you?")]
    result = classifier.classify(messages)

    assert result.tier == ModelTier.CHEAP
    assert result.score < 0.35  # Now uses cheap_ceiling=0.35
    assert len(result.reasons) > 0


def test_classifier_code_intent():
    classifier = RuleBasedClassifier(threshold=0.50)
    messages = [
        ChatMessage(
            role="user",
            content="Debug this Python function that has a memory leak and refactor the recursive approach:\n```python\nimport sys\ndef calculate_fibonacci(n: int) -> int:\n    if n <= 1:\n        return n\n    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)\n```\nAlso check the asymptotic complexity and suggest a memoization approach.",
        )
    ]
    result = classifier.classify(messages)

    assert result.tier == ModelTier.FRONTIER
    assert result.score >= 0.65  # frontier_floor=0.65
    assert any("programming" in r.lower() or "code" in r.lower() or "reasoning" in r.lower() for r in result.reasons)


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
    assert result.score >= 0.65  # frontier_floor=0.65


def test_classifier_empty_context():
    classifier = RuleBasedClassifier()
    result = classifier.classify([])
    assert result.tier == ModelTier.CHEAP


def test_jev_classifier_fallback_without_key(caplog):
    jev = JevClassifier(api_key=None)
    messages = [ChatMessage(role="user", content="Hi there")]
    with caplog.at_level("WARNING"):
        result = jev.classify(messages)

    assert result.tier == ModelTier.CHEAP
    assert "jev_mock_fallback" in result.metadata.get("provider", "")
    assert any("JEV_API_KEY" in rec.message for rec in caplog.records)


def test_jev_classifier_url_normalization():
    c1 = JevClassifier(api_key="k", base_url="https://api.typesafe.ai/v1")
    assert c1._get_endpoint_url() == "https://api.typesafe.ai/v1/systemone"

    c2 = JevClassifier(api_key="k", base_url="https://api.typesafe.ai/v1/systemone")
    assert c2._get_endpoint_url() == "https://api.typesafe.ai/v1/systemone"

    c3 = JevClassifier(api_key="k", base_url="https://api.typesafe.ai")
    assert c3._get_endpoint_url() == "https://api.typesafe.ai/v1/systemone"


def test_jev_classifier_mocked_http_cheap():
    jev = JevClassifier(api_key="test-typesafe-key")
    messages = [ChatMessage(role="user", content="What is the weather today?")]

    fake_response_data = {
        "model": "jev-1.13.0",
        "answers": {
            "tier": {
                "type": "choice",
                "choice": "cheap",
                "probabilities": {"cheap": 0.85, "medium": 0.12, "frontier": 0.03},
                "confidence": 0.82
            },
            "complexity": {
                "type": "score",
                "score": 0.20,
                "probabilities": {"0": 0.85, "1": 0.12, "2": 0.03},
                "confidence": 0.88
            }
        },
        "usage": {"input_tokens": 120, "output_tokens": 28}
    }

    from unittest.mock import patch, MagicMock
    import httpx

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "post", return_value=mock_resp) as mock_post:
        result = jev.classify(messages)

        assert mock_post.called
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-typesafe-key"
        assert "questions" in call_kwargs["json"]
        assert "tier" in call_kwargs["json"]["questions"]
        assert call_kwargs["json"]["model"] == "jev-latest"

        assert result.tier == ModelTier.CHEAP
        assert result.confidence == 0.82
        assert result.score == 0.10  # 0.20 / 2.0
        assert result.metadata["provider"] == "typesafe_jev"
        assert result.metadata["model"] == "jev-1.13.0"
        assert any("cheap" in r for r in result.reasons)


def test_jev_classifier_mocked_http_medium():
    jev = JevClassifier(api_key="test-typesafe-key")
    messages = [ChatMessage(role="user", content="Summarize this article and format as markdown list")]

    fake_response_data = {
        "model": "jev-1.13.0",
        "answers": {
            "tier": {
                "type": "choice",
                "choice": "medium",
                "probabilities": {"cheap": 0.15, "medium": 0.75, "frontier": 0.10},
                "confidence": 0.75
            },
            "complexity": {
                "type": "score",
                "score": 1.0,
                "probabilities": {"0": 0.15, "1": 0.75, "2": 0.10},
                "confidence": 0.80
            }
        },
        "usage": {"input_tokens": 140, "output_tokens": 30}
    }

    from unittest.mock import patch, MagicMock
    import httpx

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        result = jev.classify(messages)
        assert result.tier == ModelTier.MEDIUM
        assert result.confidence == 0.75
        assert result.score == 0.50
        assert result.metadata["provider"] == "typesafe_jev"


def test_jev_classifier_mocked_http_frontier():
    jev = JevClassifier(api_key="test-typesafe-key")
    messages = [ChatMessage(role="user", content="Design a distributed Byzantine Fault Tolerant consensus engine in Rust")]

    fake_response_data = {
        "model": "jev-1.13.0",
        "answers": {
            "tier": {
                "type": "choice",
                "choice": "frontier",
                "probabilities": {"cheap": 0.02, "medium": 0.08, "frontier": 0.90},
                "confidence": 0.91
            },
            "complexity": {
                "type": "score",
                "score": 1.95,
                "confidence": 0.93
            }
        },
        "usage": {"input_tokens": 160, "output_tokens": 30}
    }

    from unittest.mock import patch, MagicMock
    import httpx

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        result = jev.classify(messages)
        assert result.tier == ModelTier.FRONTIER
        assert result.confidence == 0.91
        assert result.score == 0.975
        assert result.metadata["provider"] == "typesafe_jev"


@pytest.mark.asyncio
async def test_jev_classifier_async_mocked_http():
    jev = JevClassifier(api_key="test-typesafe-key")
    messages = [ChatMessage(role="user", content="Prove Fermat's Last Theorem")]

    fake_response_data = {
        "model": "jev-1.13.0",
        "answers": {
            "tier": {
                "type": "choice",
                "choice": "frontier",
                "probabilities": {"cheap": 0.01, "medium": 0.04, "frontier": 0.95},
                "confidence": 0.95
            }
        },
        "usage": {"input_tokens": 110, "output_tokens": 20}
    }

    from unittest.mock import patch, MagicMock
    import httpx

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        result = await jev.classify_async(messages)
        assert result.tier == ModelTier.FRONTIER
        assert result.confidence == 0.95
        assert result.metadata["provider"] == "typesafe_jev"


def test_jev_classifier_fallback_on_http_error(caplog):
    jev = JevClassifier(api_key="test-typesafe-key")
    messages = [ChatMessage(role="user", content="Hello there!")]

    from unittest.mock import patch
    import httpx

    with caplog.at_level("WARNING"):
        with patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")):
            result = jev.classify(messages)

    assert result.tier == ModelTier.CHEAP
    assert result.metadata["provider"] == "jev_error_fallback"
    assert any("Fallback activated" in r for r in result.reasons)
    assert any("Jev API request failed" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_jev_classifier_async_fallback_on_http_error(caplog):
    jev = JevClassifier(api_key="test-typesafe-key")
    messages = [ChatMessage(role="user", content="Hello there!")]

    from unittest.mock import patch
    import httpx

    with caplog.at_level("WARNING"):
        with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Timed out")):
            result = await jev.classify_async(messages)

    assert result.tier == ModelTier.CHEAP
    assert result.metadata["provider"] == "jev_error_fallback"
    assert any("Fallback activated" in r for r in result.reasons)
    assert any("Async Jev API request failed" in rec.message for rec in caplog.records)


def test_jev_classifier_legacy_payload_format():
    jev = JevClassifier(api_key="test-typesafe-key")
    messages = [ChatMessage(role="user", content="Hi")]

    fake_response_data = {
        "tier": "cheap",
        "confidence": 0.88,
        "score": 0.15,
        "reasons": ["Direct tier evaluation"]
    }

    from unittest.mock import patch, MagicMock
    import httpx

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response_data
    mock_resp.raise_for_status = MagicMock()

    with patch.object(httpx.Client, "post", return_value=mock_resp):
        result = jev.classify(messages)
        assert result.tier == ModelTier.CHEAP
        assert result.confidence == 0.88
        assert result.score == 0.15


def test_jev_classifier_empty_messages():
    jev = JevClassifier(api_key="test-typesafe-key")
    result = jev.classify([])
    assert result.tier == ModelTier.CHEAP
    assert result.confidence == 1.0

