from app.router.circuit_breaker import ProviderCircuitBreaker
from app.models import ChatCompletionRequest, ChatMessage
from app.classifier import ModelTier
from app.router.engine import RouterEngine, RoutingDecision


def test_circuit_breaker_manual_trip_and_reset():
    cb = ProviderCircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)
    
    assert cb.is_available("anthropic") is True
    
    # Manually trip
    health = cb.trip_provider("anthropic", "Simulated overload")
    assert health["status"] == "tripped"
    assert cb.is_available("anthropic") is False
    assert "Simulated overload" in health["last_error"]
    
    # Reset single provider
    reset_health = cb.reset_provider("anthropic")
    assert reset_health["status"] == "healthy"
    assert cb.is_available("anthropic") is True
    assert reset_health["last_error"] is None

    # Trip multiple and reset all
    cb.trip_provider("openai")
    cb.trip_provider("google")
    assert cb.is_available("openai") is False
    assert cb.is_available("google") is False
    
    all_health = cb.reset_all()
    assert all_health["openai"]["status"] == "healthy"
    assert all_health["google"]["status"] == "healthy"
    assert cb.is_available("openai") is True
    assert cb.is_available("google") is True


def test_chaos_api_endpoints(client):
    # Test trip endpoint
    res = client.post("/v1/chaos/trip", json={"provider": "xai", "reason": "Simulated Grok timeout"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "tripped"
    assert data["provider"] == "xai"
    assert data["all_health"]["xai"]["status"] == "tripped"

    # Verify through GET /v1/providers/health
    health_res = client.get("/v1/providers/health")
    assert health_res.status_code == 200
    assert health_res.json()["xai"]["status"] == "tripped"

    # Test reset endpoint
    reset_res = client.post("/v1/chaos/reset", json={"provider": "xai"})
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["status"] == "reset"
    assert reset_data["all_health"]["xai"]["status"] == "healthy"

    # Reset all
    reset_all_res = client.post("/v1/chaos/reset", json={"provider": "all"})
    assert reset_all_res.status_code == 200


def test_router_prioritizes_healthy_providers_over_tripped():
    engine = RouterEngine()
    
    # Trip anthropic
    engine.circuit_breaker.trip_provider("anthropic", "Simulated outage")
    
    decision = RoutingDecision(
        tier=ModelTier.CHEAP,
        model_name="mistral/mistral-small-4",
        backend=engine.cheap_backend,
        provider_name="mistral",
        classifier_score=0.1,
        reasons=["Test decision"],
    )
    
    candidates = engine.get_fallback_candidates(decision)
    assert len(candidates) > 0

    # Healthy providers should appear before any tripped provider
    tripped_indices = [
        i for i, c in enumerate(candidates) if c.provider_name.lower() == "anthropic"
    ]
    healthy_indices = [
        i for i, c in enumerate(candidates) if c.provider_name.lower() != "anthropic"
    ]

    if tripped_indices and healthy_indices:
        assert min(tripped_indices) > min(healthy_indices)

    # Clean up
    engine.circuit_breaker.reset_all()


def test_circuit_breaker_latency_tracking():
    cb = ProviderCircuitBreaker()
    cb.record_latency("mistral", 45.2)
    cb.record_latency("mistral", 55.8)
    cb.record_success("mistral")

    health = cb.get_health_status()
    assert "mistral" in health
    assert health["mistral"]["last_latency_ms"] == 55.8
    assert health["mistral"]["avg_latency_ms"] == 50.5
    assert health["mistral"]["availability_rate_pct"] == 100.0


def test_probe_providers_endpoint(client):
    res = client.post("/v1/providers/probe", json={"providers": ["anthropic", "openai"]})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["total_probed"] == 2
    assert "anthropic" in data["probes"]
    assert "openai" in data["probes"]
    assert data["probes"]["anthropic"]["latency_ms"] > 0
    assert data["probes"]["anthropic"]["available"] is True

