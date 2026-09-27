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
    assert "router-auto" in model_ids
    assert "router-cheap" in model_ids
    assert "router-frontier" in model_ids


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

    recent_res = client.get("/v1/metrics/recent?limit=5")
    assert recent_res.status_code == 200
    recent = recent_res.json()
    assert isinstance(recent, list)
