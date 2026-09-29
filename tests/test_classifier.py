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


def test_classifier_domain_intents():
    classifier = RuleBasedClassifier()

    # Proof intent
    res_proof = classifier.classify([ChatMessage(role="user", content="Prove that the halting problem is undecidable.")])
    assert res_proof.detected_intent == "formal_reasoning"
    assert "Proof" in res_proof.tags

    # Architecture intent
    res_arch = classifier.classify([ChatMessage(role="user", content="Design a distributed system architecture with microservices and consensus.")])
    assert res_arch.detected_intent == "system_architecture"
    assert "Architecture" in res_arch.tags

    # Coding intent
    res_code = classifier.classify([ChatMessage(role="user", content="Debug this python script that has a bug in DFS graph traversal.")])
    assert res_code.detected_intent == "code_engineering"
    assert "Coding" in res_code.tags

    # Summary intent
    res_sum = classifier.classify([ChatMessage(role="user", content="Summarize this article into 3 key takeaways and bullet points.")])
    assert res_sum.detected_intent == "content_summary"
    assert "Summary" in res_sum.tags

    # Creative intent
    res_creat = classifier.classify([ChatMessage(role="user", content="Write a creative short story about an AI in neo-tokyo.")])
    assert res_creat.detected_intent == "creative_writing"
    assert "Creative" in res_creat.tags


def test_classifier_category_distinctness():
    classifier = RuleBasedClassifier()

    # Code prompt should have high Coding, lower Creative/Summary
    code_res = classifier.classify([ChatMessage(role="user", content="def binary_search(arr, target):\n    pass")])
    assert code_res.category_scores["Coding"] > 0.4
    assert code_res.category_scores["Creative"] < 0.2

    # Creative prompt should have high Creative, zero Coding
    creat_res = classifier.classify([ChatMessage(role="user", content="Write a poem and a short story about the stars.")])
    assert creat_res.category_scores["Creative"] > 0.4
    assert creat_res.category_scores["Coding"] == 0.0


def test_classifier_decision_trace():
    classifier = RuleBasedClassifier()
    res = classifier.classify([ChatMessage(role="user", content="def solve_knapsack():\n    pass")])
    assert res.decision_trace is not None
    trace = res.decision_trace
    assert "baseline_score" in trace
    assert "signals" in trace
    assert any(s["signal"] == "Programming Syntax" for s in trace["signals"])
    assert "calculated_score" in trace
    assert "thresholds" in trace


def test_classifier_strategy_profiles():
    classifier = RuleBasedClassifier()
    # Moderate complexity prompt: has some code/structure, moderate score
    msg = [ChatMessage(role="user", content="Can you explain how quicksort partition works in Python?\n```python\ndef partition(arr, low, high):\n    pass\n```")]

    res_balanced = classifier.classify(msg, strategy="balanced")
    res_cost = classifier.classify(msg, strategy="cost_optimized")
    res_quality = classifier.classify(msg, strategy="quality_optimized")

    # Verify thresholds in decision traces
    assert res_balanced.decision_trace["strategy"] == "balanced"
    assert res_balanced.decision_trace["thresholds"] == {"cheap_ceiling": 0.35, "frontier_floor": 0.65}

    assert res_cost.decision_trace["strategy"] == "cost_optimized"
    assert res_cost.decision_trace["thresholds"] == {"cheap_ceiling": 0.45, "frontier_floor": 0.75}

    assert res_quality.decision_trace["strategy"] == "quality_optimized"
    assert res_quality.decision_trace["thresholds"] == {"cheap_ceiling": 0.25, "frontier_floor": 0.50}

    # Scores should be identical since the prompt is the same, but the assigned tier can shift
    assert res_balanced.score == res_cost.score == res_quality.score

    # Quality optimized should be at least as high tier as balanced, and balanced at least as high as cost
    tier_rank = {ModelTier.CHEAP: 0, ModelTier.MEDIUM: 1, ModelTier.FRONTIER: 2}
    assert tier_rank[res_quality.tier] >= tier_rank[res_balanced.tier] >= tier_rank[res_cost.tier]


def test_classifier_multilang_simple_patterns():
    """Multi-language simple patterns should route to cheap tier."""
    classifier = RuleBasedClassifier()

    # French greeting
    res_fr = classifier.classify([ChatMessage(role="user", content="Bonjour!")])
    assert res_fr.tier == ModelTier.CHEAP, f"French greeting should be cheap, got {res_fr.tier}"

    # Spanish greeting
    res_es = classifier.classify([ChatMessage(role="user", content="Hola!")])
    assert res_es.tier == ModelTier.CHEAP, f"Spanish greeting should be cheap, got {res_es.tier}"

    # German greeting
    res_de = classifier.classify([ChatMessage(role="user", content="Guten Tag!")])
    assert res_de.tier == ModelTier.CHEAP, f"German greeting should be cheap, got {res_de.tier}"

    # Portuguese
    res_pt = classifier.classify([ChatMessage(role="user", content="Bom dia!")])
    assert res_pt.tier == ModelTier.CHEAP, f"Portuguese greeting should be cheap, got {res_pt.tier}"

    # Multi-language thank you
    res_ty = classifier.classify([ChatMessage(role="user", content="Gracias!")])
    assert res_ty.tier == ModelTier.CHEAP

    res_dk = classifier.classify([ChatMessage(role="user", content="Danke!")])
    assert res_dk.tier == ModelTier.CHEAP


def test_classifier_multilang_complex_reasoning():
    """French and Spanish complex reasoning should route to frontier."""
    classifier = RuleBasedClassifier()

    # French: formal verification / abstract algebra
    res_fr = classifier.classify([ChatMessage(role="user", content="Démontre la vérification formelle de ce théorème en algèbre abstraite.")])
    assert res_fr.tier == ModelTier.FRONTIER, f"French complex reasoning should be frontier, got {res_fr.tier}"

    # Spanish: distributed system design
    res_es = classifier.classify([ChatMessage(role="user", content="Diseña un sistema distribuido con verificación formal y ecuación diferencial.")])
    assert res_es.tier == ModelTier.FRONTIER, f"Spanish complex reasoning should be frontier, got {res_es.tier}"


def test_classifier_math_latex_detection():
    """LaTeX math notation should trigger frontier tier."""
    classifier = RuleBasedClassifier()

    # LaTeX fractions and integrals (using raw string to preserve backslashes)
    latex_prompt = r"Solve \frac{d}{dx} \int_0^x f(t) dt and prove the result using the Leibniz integral rule and the fundamental theorem of calculus."
    res_latex = classifier.classify([ChatMessage(role="user", content=latex_prompt)])
    assert res_latex.tier == ModelTier.FRONTIER, f"LaTeX math should be frontier, got {res_latex.tier} (score={res_latex.score})"
    assert any("Math" in r or "LaTeX" in r for r in res_latex.reasons)

    # Unicode math symbols
    res_unicode = classifier.classify([ChatMessage(role="user", content="Prove that ∀x ∈ ℝ, ∃y such that x ≤ y → x ≠ ∞")])
    assert res_unicode.tier == ModelTier.FRONTIER, f"Unicode math should be frontier, got {res_unicode.tier}"


def test_classifier_structured_output_detection():
    """Requests for structured output (JSON, schema) should be detected as medium+."""
    classifier = RuleBasedClassifier()

    res = classifier.classify([ChatMessage(role="user", content="Convert this data to a JSON schema and validate the OpenAPI spec.")])
    assert res.tier in (ModelTier.MEDIUM, ModelTier.FRONTIER), f"Structured output should be medium+, got {res.tier}"
    assert res.score >= 0.35  # At least above cheap ceiling


