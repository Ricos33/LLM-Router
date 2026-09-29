import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.router.rules import RoutingRule, RoutingRuleManager, DEFAULT_RULES
from app.models import ChatCompletionRequest, ChatMessage
from app.router.engine import RouterEngine
from app.classifier.types import ModelTier


@pytest.fixture
def client():
    return TestClient(app)


def test_default_rules_loaded():
    mgr = RoutingRuleManager()
    rules = mgr.get_all_rules()
    assert len(rules) >= 4
    rule_ids = [r.id for r in rules]
    assert "sql-database-optimization" in rule_ids
    assert "math-formal-proofs" in rule_ids
    assert "cybersecurity-audit" in rule_ids
    assert "quick-greetings-micro" in rule_ids


def test_rule_matching_sql():
    mgr = RoutingRuleManager()
    msgs = [{"role": "user", "content": "How do I optimize a complex PostgreSQL database schema with indexing strategy?"}]
    match = mgr.evaluate(msgs)
    assert match is not None
    assert match.rule_id == "sql-database-optimization"
    assert match.target_model == "anthropic/claude-sonnet-5"
    assert match.target_tier == "medium"


def test_rule_matching_math():
    mgr = RoutingRuleManager()
    msgs = [{"role": "user", "content": "Prove by mathematical induction that 1 + 2 + ... + n = n(n+1)/2"}]
    match = mgr.evaluate(msgs)
    assert match is not None
    assert match.rule_id == "math-formal-proofs"
    assert match.target_model == "openai/gpt-6-astra"
    assert match.target_tier == "frontier"


def test_rule_matching_greetings():
    mgr = RoutingRuleManager()
    msgs = [{"role": "user", "content": "Hello!"}]
    match = mgr.evaluate(msgs)
    assert match is not None
    assert match.rule_id == "quick-greetings-micro"
    assert match.target_model == "mistral/mistral-small-4"
    assert match.target_tier == "cheap"


def test_rule_crud_operations():
    mgr = RoutingRuleManager()
    custom = RoutingRule(
        id="test-custom-finance",
        name="Finance Routing",
        priority=200,
        keywords=["ebitda", "quarterly earnings"],
        target_tier="medium",
        target_model="mistral/mistral-large-3",
    )
    mgr.add_rule(custom)
    assert mgr.get_rule("test-custom-finance") is not None

    match = mgr.evaluate([{"role": "user", "content": "Analyze our Q3 EBITDA"}])
    assert match is not None
    assert match.rule_id == "test-custom-finance"

    # Delete
    deleted = mgr.delete_rule("test-custom-finance")
    assert deleted is True
    assert mgr.get_rule("test-custom-finance") is None

    # Reset
    mgr.reset_defaults()
    assert len(mgr.get_all_rules()) == len(DEFAULT_RULES)


def test_router_engine_decide_route_with_rule():
    engine = RouterEngine()
    req = ChatCompletionRequest(
        model="router-auto",
        messages=[ChatMessage(role="user", content="Explain postgresql database schema partitioning and query optimization.")]
    )
    decision = engine.decide_route(req)
    assert decision.matched_rule == "sql-database-optimization"
    assert decision.model_name == "anthropic/claude-sonnet-5"
    assert decision.tier == ModelTier.MEDIUM


def test_api_rules_endpoints(client):
    # 1. GET /v1/rules
    resp = client.get("/v1/rules")
    assert resp.status_code == 200
    data = resp.json()
    assert "rules" in data
    assert len(data["rules"]) >= 4

    # 2. POST /v1/rules
    new_rule = {
        "id": "e2e-api-rule",
        "name": "E2E Rule",
        "description": "Rule created via API",
        "priority": 150,
        "keywords": ["kubernetes-ingress-cert"],
        "target_tier": "frontier",
        "target_model": "anthropic/claude-opus-5.5"
    }
    resp = client.post("/v1/rules", json=new_rule)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # 3. Verify rule is active via classify
    resp = client.post("/v1/classify", json={
        "messages": [{"role": "user", "content": "Debug kubernetes-ingress-cert"}]
    })
    assert resp.status_code == 200
    classify_data = resp.json()
    assert any("rule:e2e-api-rule" in tag for tag in classify_data.get("tags", []))
    assert classify_data.get("suggested_model") == "anthropic/claude-opus-5.5"

    # 4. DELETE /v1/rules/e2e-api-rule
    resp = client.delete("/v1/rules/e2e-api-rule")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    # 5. POST /v1/rules/reset
    resp = client.post("/v1/rules/reset")
    assert resp.status_code == 200
