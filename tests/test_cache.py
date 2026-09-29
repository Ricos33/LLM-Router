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
