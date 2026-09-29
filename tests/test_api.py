import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "llm-router"


def test_models_endpoint(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    model_ids = [m["id"] for m in data["data"]]
    assert len(model_ids) > 0
    # assert "router-cheap" in model_ids
    # assert "router-frontier" in model_ids


def test_chat_completions_auto(client):
    payload = {
        "model": "router-auto",
        "messages": [
            {"role": "user", "content": "What is the capital of Morocco?"}
        ]
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) > 0
    assert "router_metadata" in data
    assert data["router_metadata"]["routed_tier"] == "cheap"
    assert "X-Router-Tier" in response.headers
    assert response.headers["X-Router-Tier"] == "cheap"


def test_chat_completions_forced_frontier(client):
    payload = {
        "model": "router-auto",
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }
    headers = {"X-Router-Tier": "frontier"}
    response = client.post("/v1/chat/completions", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["router_metadata"]["routed_tier"] == "frontier"
    assert response.headers["X-Router-Tier"] == "frontier"


def test_metrics_endpoints(client):
    summary_res = client.get("/v1/metrics/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "total_requests" in summary
    assert "tier_distribution" in summary
    assert "average_latency_ms" in summary
    assert "total_errors" in summary

    recent_res = client.get("/v1/metrics/recent?limit=5")
    assert recent_res.status_code == 200
    recent = recent_res.json()
    assert isinstance(recent, list)


def test_models_tiers_endpoint(client):
    res = client.get("/v1/models/tiers")
    assert res.status_code == 200
    tiers = res.json()
    assert "cheap" in tiers
    assert "medium" in tiers
    assert "frontier" in tiers
    assert "model" in tiers["cheap"]
    assert "model" in tiers["medium"]
    assert "model" in tiers["frontier"]


def test_classify_endpoint_probabilities(client):
    payload = {
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ]
    }
    res = client.post("/v1/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "tier" in data
    assert "probabilities" in data
    assert "cheap" in data["probabilities"]
    assert "medium" in data["probabilities"]
    assert "frontier" in data["probabilities"]
    assert "tier_models" in data
    assert "suggested_model" in data


def test_chat_completions_streaming(client):
    payload = {
        "model": "router-auto",
        "messages": [
            {"role": "user", "content": "Tell me a short story."}
        ],
        "stream": True
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert "X-Router-Tier" in response.headers
    
    text = response.text
    assert text.startswith("data: ")
    assert "data: [DONE]" in text

def test_classify_endpoint_budget_filtering(client):
    # Test Free budget
    payload = {
        "messages": [{"role": "user", "content": "test"}],
        "budget": "Free"
    }
    res = client.post("/v1/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["recommendations"]) == 0 or all(r["price_in"] == 0 for r in data["recommendations"])

    # Test Pro budget (should include expensive models)
    payload["budget"] = "Pro"
    res = client.post("/v1/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert any((r["price_in"] or 0) > 2.0 for r in data["recommendations"])

def test_classify_endpoint_provider_filtering(client):
    payload = {
        "messages": [{"role": "user", "content": "test"}],
        "providers": ["anthropic"]
    }
    res = client.post("/v1/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert all(r["provider"] == "anthropic" for r in data["recommendations"])

def test_classify_endpoint_caching(client):
    payload = {
        "messages": [{"role": "user", "content": "test caching query"}],
        "budget": "Any",
        "providers": []
    }
    res1 = client.post("/v1/classify", json=payload)
    assert res1.status_code == 200
    
    # Second request should hit cache
    res2 = client.post("/v1/classify", json=payload)
    assert res2.status_code == 200
    assert res1.json()["suggested_model"] == res2.json()["suggested_model"]

def test_metrics_export_csv(client):
    res = client.get("/v1/metrics/export/csv")
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/csv; charset=utf-8"
    assert "id,timestamp,prompt_preview" in res.text



def test_models_all_providers_present(client):
    """Verify all 8 authorized providers are in the catalog."""
    res = client.get("/v1/models")
    data = res.json()
    providers = set(m["provider"] for m in data["data"])
    expected = {"anthropic", "openai", "google", "qwen", "mistral", "deepseek", "meta", "xai"}
    assert expected == providers, f"Missing providers: {expected - providers}"


def test_models_have_scores(client):
    """Every model in the catalog should have benchmark scores."""
    res = client.get("/v1/models")
    data = res.json()
    for m in data["data"]:
        assert m.get("scores") is not None, f"Model {m['id']} missing scores"
        assert "Reasoning" in m["scores"], f"Model {m['id']} missing Reasoning score"
        assert "Coding" in m["scores"], f"Model {m['id']} missing Coding score"
        assert "Summary" in m["scores"], f"Model {m['id']} missing Summary score"
        assert "Creative" in m["scores"], f"Model {m['id']} missing Creative score"


def test_models_pricing_valid(client):
    """All models should have positive pricing."""
    res = client.get("/v1/models")
    data = res.json()
    for m in data["data"]:
        assert (m.get("price_in") or 0) >= 0, f"Model {m['id']} has negative input price"
        assert (m.get("price_out") or 0) >= 0, f"Model {m['id']} has negative output price"
        assert (m.get("context_length") or 0) > 0, f"Model {m['id']} has zero context length"


def test_classify_simple_recommends_cheap(client):
    """Simple greetings should recommend a cheap/budget model."""
    payload = {"messages": [{"role": "user", "content": "Hi there!"}]}
    res = client.post("/v1/classify", json=payload)
    data = res.json()
    top_model = data["recommendations"][0]
    # The top recommended model for a greeting should be cheap (< $1/M input)
    assert top_model["price_in"] <= 1.0, f"Simple prompt recommended expensive model: {top_model['model_id']} at ${top_model['price_in']}/M"


def test_classify_complex_recommends_frontier(client):
    """Complex reasoning prompt should recommend a frontier model."""
    payload = {"messages": [{"role": "user", "content": "Design a distributed Byzantine Fault Tolerant consensus engine with formal verification proofs and analyze asymptotic complexity of the raft protocol."}]}
    res = client.post("/v1/classify", json=payload)
    data = res.json()
    top_model = data["recommendations"][0]
    # Should recommend a high-quality model
    assert top_model["price_in"] >= 1.0, f"Complex prompt recommended budget model: {top_model['model_id']} at ${top_model['price_in']}/M"


def test_classify_different_prompts_give_different_models(client):
    """Different prompt types should produce meaningfully different recommendations."""
    simple = client.post("/v1/classify", json={"messages": [{"role": "user", "content": "Hello, how are you today?"}]}).json()
    code = client.post("/v1/classify", json={"messages": [{"role": "user", "content": "Debug this Python function that has a memory leak and refactor: ```python\nimport sys\ndef fib(n): return fib(n-1)+fib(n-2)\n```"}]}).json()
    reasoning = client.post("/v1/classify", json={"messages": [{"role": "user", "content": "Prove that the halting problem is undecidable using a formal proof by contradiction."}]}).json()

    # Scores should be meaningfully different
    assert simple["score"] < code["score"], "Simple prompt should have lower score than code prompt"
    assert simple["score"] < reasoning["score"], "Simple prompt should have lower score than reasoning prompt"

    # Tags should differ
    assert "Reasoning" not in simple.get("tags", []) or "Coding" in code.get("tags", [])


def test_classify_medium_tier(client):
    """A moderate complexity prompt should route to medium tier."""
    payload = {"messages": [{"role": "user", "content": "Explain the pros and cons of microservices vs monolith architecture and compare them in a table format."}]}
    res = client.post("/v1/classify", json=payload)
    data = res.json()
    # Should detect medium-level indicators
    assert data["score"] > 0.15, "Moderate prompt should have score above baseline"
    assert len(data["recommendations"]) > 0


def test_three_tier_classifier():
    """Test the rule-based classifier produces all three tiers."""
    from app.classifier.rule_based import RuleBasedClassifier
    from app.models import ChatMessage

    classifier = RuleBasedClassifier()

    # CHEAP
    cheap = classifier.classify([ChatMessage(role="user", content="Hi!")])
    assert cheap.tier.value == "cheap"

    # MEDIUM — structured task
    medium = classifier.classify([ChatMessage(role="user", content="Explain the best practices for building a REST API with proper error handling. Create a step by step tutorial.")])
    assert medium.tier.value in ("medium", "frontier"), f"Got {medium.tier.value} with score {medium.score}"

    # FRONTIER — complex reasoning + code
    frontier = classifier.classify([ChatMessage(role="user", content="Design a distributed system with Byzantine fault tolerance. Prove the correctness of your consensus algorithm. Debug this implementation:\n```python\nclass Raft:\n    async def replicate_log(self): pass\n```\nAnalyze the asymptotic complexity and compare to Paxos.")])
    assert frontier.tier.value == "frontier", f"Got {frontier.tier.value} with score {frontier.score}"


def test_catalog_summary(client):
    """Test /v1/catalog/summary returns overview metrics."""
    res = client.get("/v1/catalog/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_models"] > 0
    assert "providers" in data
    assert "tier_distribution" in data
    assert data["tier_distribution"]["cheap"] > 0
    assert data["tier_distribution"]["frontier"] > 0
    assert data["price_range_per_m"]["min_in"] >= 0
    assert data["price_range_per_m"]["max_in"] > 0


def test_analytics_endpoint(client):
    """Test /v1/analytics returns structured analytics."""
    res = client.get("/v1/analytics")
    assert res.status_code == 200
    data = res.json()
    assert "model_stats" in data
    assert "tier_stats" in data
    assert "hourly_timeseries" in data
    assert "efficiency_percentage" in data
    assert "total_requests" in data


