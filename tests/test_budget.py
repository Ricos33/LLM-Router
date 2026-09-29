import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.router.budget import BudgetManager, BudgetAlertEvent
from app.config import settings


def test_budget_manager_initial_unlimited():
    bm = BudgetManager(webhook_url="", thresholds=[50.0, 80.0, 100.0])
    status = bm.get_status(current_cost=12.50, budget_limit=0.0)
    assert status["status"] == "unlimited"
    assert status["monthly_budget_usd"] == 0.0
    assert status["current_cost_usd"] == 12.50
    assert status["remaining_usd"] is None
    assert status["percent_used"] == 0.0
    assert status["alert_count"] == 0


def test_budget_manager_threshold_triggers():
    bm = BudgetManager(webhook_url="", thresholds=[50.0, 80.0, 100.0])
    
    # 40% spend - no alert
    alert = bm.check_and_notify(current_cost=40.0, budget_limit=100.0)
    assert alert is None
    assert len(bm.alert_history) == 0

    # 55% spend - triggers 50% alert
    alert = bm.check_and_notify(current_cost=55.0, budget_limit=100.0)
    assert alert is not None
    assert alert.threshold_pct == 50.0
    assert "55.0% used" in alert.message
    assert len(bm.alert_history) == 1

    # Repeat at 56% - does NOT re-trigger 50%
    alert2 = bm.check_and_notify(current_cost=56.0, budget_limit=100.0)
    assert alert2 is None
    assert len(bm.alert_history) == 1

    # Jump to 85% - triggers 80% warning
    alert3 = bm.check_and_notify(current_cost=85.0, budget_limit=100.0)
    assert alert3 is not None
    assert alert3.threshold_pct == 80.0
    assert "[WARNING]" in alert3.message
    assert len(bm.alert_history) == 2

    # Cross 100% - triggers 100% critical
    alert4 = bm.check_and_notify(current_cost=105.0, budget_limit=100.0)
    assert alert4 is not None
    assert alert4.threshold_pct == 100.0
    assert "[CRITICAL]" in alert4.message
    assert len(bm.alert_history) == 3

    # Check status
    status = bm.get_status(current_cost=105.0, budget_limit=100.0)
    assert status["status"] == "critical"
    assert status["remaining_usd"] == 0.0
    assert status["percent_used"] == 105.0
    assert status["alert_count"] == 3


def test_budget_manager_clear_alerts():
    bm = BudgetManager(webhook_url="", thresholds=[50.0, 80.0, 100.0])
    bm.check_and_notify(current_cost=90.0, budget_limit=100.0)
    assert len(bm.alert_history) == 2  # 50% and 80% fired

    bm.clear_alerts()
    assert len(bm.alert_history) == 0
    assert len(bm.fired_thresholds) == 0

    # Can fire again after clear
    alert = bm.check_and_notify(current_cost=90.0, budget_limit=100.0)
    assert alert is not None


def test_budget_manager_test_alert():
    bm = BudgetManager()
    res = bm.trigger_test_alert()
    assert res["success"] is True
    assert res["alert"]["threshold_pct"] == 80.0
    assert "[TEST]" in res["alert"]["message"]
    assert len(bm.alert_history) == 1


def test_budget_api_endpoints():
    client = TestClient(app)

    # 1. Get status
    resp = client.get("/v1/budget/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "current_cost_usd" in data
    assert "thresholds" in data

    # 2. Configure budget
    orig_budget = settings.monthly_budget_usd
    try:
        conf_resp = client.post("/v1/budget/configure", json={
            "monthly_budget_usd": 50.0,
            "webhook_url": "https://example.com/webhook",
            "thresholds": [50.0, 75.0, 95.0, 100.0]
        })
        assert conf_resp.status_code == 200
        conf_data = conf_resp.json()
        assert conf_data["success"] is True
        assert conf_data["status"]["monthly_budget_usd"] == 50.0
        assert conf_data["status"]["webhook_configured"] is True
        assert conf_data["status"]["thresholds"] == [50.0, 75.0, 95.0, 100.0]

        # 3. Test alert
        test_resp = client.post("/v1/budget/test-alert", json={})
        assert test_resp.status_code == 200
        assert test_resp.json()["success"] is True

        # 4. Clear alerts
        clear_resp = client.post("/v1/budget/clear-alerts")
        assert clear_resp.status_code == 200
        assert clear_resp.json()["success"] is True

        # Status alert_count should be 0
        status_resp = client.get("/v1/budget/status")
        assert status_resp.json()["alert_count"] == 0

    finally:
        # Restore original budget
        client.post("/v1/budget/configure", json={
            "monthly_budget_usd": orig_budget,
            "webhook_url": "",
            "thresholds": [50.0, 80.0, 90.0, 100.0]
        })
