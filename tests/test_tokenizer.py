"""Tests for the token estimation and cost preview system."""
import pytest
from app.tokenizer import estimate_tokens, estimate_messages_tokens, estimate_cost, estimate_cost_all_models


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_short_text():
    tokens = estimate_tokens("Hello world")
    assert 1 <= tokens <= 5  # Should be ~2 tokens


def test_estimate_tokens_code():
    code = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)"""
    tokens = estimate_tokens(code)
    assert 15 <= tokens <= 50  # Reasonable range for this code


def test_estimate_tokens_long_text():
    text = "This is a test sentence. " * 100
    tokens = estimate_tokens(text)
    assert 300 <= tokens <= 800  # ~500 words -> ~650 tokens


def test_estimate_messages_tokens():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]
    tokens = estimate_messages_tokens(messages)
    assert tokens > 10  # At least some tokens
    assert tokens < 100  # Not unreasonably many


def test_estimate_cost_known_model():
    result = estimate_cost("meta/llama-4-scout", prompt_tokens=1000, estimated_completion_tokens=500)
    assert result is not None
    assert result["model_id"] == "meta/llama-4-scout"
    assert result["cost_total_usd"] > 0
    assert result["fits_context"] is True


def test_estimate_cost_unknown_model():
    result = estimate_cost("nonexistent/model", prompt_tokens=1000)
    assert result is None


def test_estimate_cost_with_caching():
    result = estimate_cost(
        "anthropic/claude-opus-5.5",
        prompt_tokens=10000,
        estimated_completion_tokens=1000,
        cache_hit_rate=0.8,
    )
    assert result is not None
    assert result["cost_cached_total_usd"] is not None
    assert result["cost_cached_total_usd"] < result["cost_total_usd"]
    assert result["cache_savings_pct"] > 0


def test_estimate_cost_all_models_sorted():
    results = estimate_cost_all_models(prompt_tokens=5000, estimated_completion_tokens=1000)
    assert len(results) > 0
    # Should be sorted by cost ascending
    costs = [r["cost_total_usd"] for r in results]
    assert costs == sorted(costs)


def test_estimate_cost_all_models_tier_filter():
    results = estimate_cost_all_models(prompt_tokens=5000, tier_filter="cheap")
    assert len(results) > 0
    assert all(r["tier"] == "cheap" for r in results)


def test_estimate_cost_all_models_provider_filter():
    results = estimate_cost_all_models(prompt_tokens=5000, provider_filter="anthropic")
    assert len(results) > 0
    assert all(r["provider"] == "anthropic" for r in results)


# API endpoint test
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_estimate_cost_api():
    resp = client.post("/v1/estimate-cost", json={
        "messages": [{"role": "user", "content": "Explain quantum computing in simple terms."}],
        "estimated_completion_tokens": 500,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "prompt_tokens_estimated" in data
    assert "estimates" in data
    assert "summary" in data
    assert len(data["estimates"]) > 0
    assert data["summary"]["cheapest_cost_usd"] <= data["summary"]["most_expensive_cost_usd"]
    assert data["summary"]["savings_percentage"] >= 0


def test_estimate_cost_api_with_filters():
    resp = client.post("/v1/estimate-cost", json={
        "messages": [{"role": "user", "content": "Hello"}],
        "tier": "frontier",
        "cache_hit_rate": 0.8,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["tier"] == "frontier" for e in data["estimates"])
