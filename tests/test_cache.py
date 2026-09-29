import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_gateway_cache():
    # Enable cache
    settings.gateway_cache_enabled = True
    
    # Clear cache first
    client.post("/v1/cache/clear")

    # First request
    req1 = {
        "model": "router-auto",
        "messages": [{"role": "user", "content": "What is semantic cache?"}],
        "temperature": 0.5
    }
    
    resp1 = client.post("/v1/chat/completions", json=req1)
    assert resp1.status_code == 200
    assert "X-Gateway-Cache" not in resp1.headers
    
    # Second request (identical)
    resp2 = client.post("/v1/chat/completions", json=req1)
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Gateway-Cache") == "HIT"
    assert resp2.json()["router_metadata"]["gateway_cache_hit"] is True
    assert resp2.json()["router_metadata"]["cost_actual_usd"] == 0.0

    # Third request (different temperature -> cache miss)
    req3 = req1.copy()
    req3["temperature"] = 0.6
    resp3 = client.post("/v1/chat/completions", json=req3)
    assert resp3.status_code == 200
    assert "X-Gateway-Cache" not in resp3.headers

    # Clear cache
    client.post("/v1/cache/clear")
    resp4 = client.post("/v1/chat/completions", json=req1)
    assert resp4.status_code == 200
    assert "X-Gateway-Cache" not in resp4.headers

    # Disable cache
    settings.gateway_cache_enabled = False


def test_semantic_cache_near_match():
    """Semantic cache: near-identical prompts should produce a cache hit."""
    settings.gateway_cache_enabled = True
    client.post("/v1/cache/clear")

    # Original prompt
    req_original = {
        "model": "router-auto",
        "messages": [{"role": "user", "content": "Explain the concept of quantum computing"}],
        "temperature": 0.5
    }
    resp1 = client.post("/v1/chat/completions", json=req_original)
    assert resp1.status_code == 200
    assert "X-Gateway-Cache" not in resp1.headers

    # Near-identical prompt (articles + filler removed should match)
    req_near = {
        "model": "router-auto",
        "messages": [{"role": "user", "content": "Please explain the concept of quantum computing"}],
        "temperature": 0.5
    }
    resp2 = client.post("/v1/chat/completions", json=req_near)
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Gateway-Cache") == "HIT"
    assert resp2.json()["router_metadata"]["gateway_cache_hit"] is True

    # Very different prompt -> cache miss
    req_diff = {
        "model": "router-auto",
        "messages": [{"role": "user", "content": "Write me a poem about the ocean"}],
        "temperature": 0.5
    }
    resp3 = client.post("/v1/chat/completions", json=req_diff)
    assert resp3.status_code == 200
    assert "X-Gateway-Cache" not in resp3.headers

    # Cleanup
    client.post("/v1/cache/clear")
    settings.gateway_cache_enabled = False


def test_cache_stats_endpoint():
    """Cache stats endpoint returns valid statistics."""
    settings.gateway_cache_enabled = True
    client.post("/v1/cache/clear")

    # Populate cache
    req = {
        "model": "router-auto",
        "messages": [{"role": "user", "content": "Stats test prompt"}],
        "temperature": 0.5
    }
    client.post("/v1/chat/completions", json=req)
    # Hit cache
    client.post("/v1/chat/completions", json=req)

    resp = client.get("/v1/cache/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert "hit_count" in stats
    assert "miss_count" in stats
    assert "semantic_hit_count" in stats
    assert "hit_rate" in stats
    assert "savings_usd" in stats
    assert stats["hit_count"] >= 1

    client.post("/v1/cache/clear")
    settings.gateway_cache_enabled = False


def test_cache_normalizer():
    """Unit test for the aggressive text normalizer."""
    from app.router.response_cache import _normalize_text

    # Articles and fillers removed; "please" and "the" are stripped
    result = _normalize_text("Please explain the concept of quantum computing")
    assert "quantum computing" in result
    assert "please" not in result
    assert "the " not in result.split()
    # Punctuation stripped
    assert _normalize_text("Hello, world!") == "hello world"
    # Multiple spaces collapsed
    assert _normalize_text("hello   world   test") == "hello world test"
    # Accents stripped
    norm_accents = _normalize_text("café résumé")
    assert "cafe" in norm_accents


def test_similarity_function():
    """Unit test for the similarity scoring function."""
    from app.router.response_cache import _similarity, _normalize_text

    a = _normalize_text("Explain quantum computing concepts")
    b = _normalize_text("Please explain the quantum computing concepts")
    assert _similarity(a, b) >= 0.90

    c = _normalize_text("Write a haiku about cats")
    assert _similarity(a, c) < 0.5

    # Identical
    assert _similarity(a, a) == 1.0

    # Empty
    assert _similarity("", "hello") == 0.0
