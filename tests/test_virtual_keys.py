"""Tests for Virtual API Key management (Backlog Item 4)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_virtual_key():
    """Create a new virtual API key."""
    resp = client.post("/v1/keys", json={
        "name": "test-team",
        "budget_usd": 50.0,
        "rate_limit_rpm": 30,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "created"
    key = data["key"]
    assert key["name"] == "test-team"
    assert key["key_id"].startswith("sk-router-")
    assert key["budget_usd"] == 50.0
    assert key["rate_limit_rpm"] == 30
    assert key["is_active"] is True
    assert key["spent_usd"] == 0.0


def test_list_virtual_keys():
    """List all virtual keys."""
    # Create a key first
    client.post("/v1/keys", json={"name": "list-test"})
    resp = client.get("/v1/keys")
    assert resp.status_code == 200
    data = resp.json()
    assert "keys" in data
    assert len(data["keys"]) >= 1
    # Check that keys have a preview (masked)
    for k in data["keys"]:
        assert "key_preview" in k


def test_revoke_virtual_key():
    """Revoke a virtual key."""
    # Create
    create_resp = client.post("/v1/keys", json={"name": "revoke-test"})
    key_id = create_resp.json()["key"]["key_id"]

    # Revoke
    resp = client.post(f"/v1/keys/{key_id}/revoke")
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"

    # Validate should fail
    resp2 = client.post("/v1/keys/validate", headers={"Authorization": f"Bearer {key_id}"})
    assert resp2.status_code == 403
    assert "revoked" in resp2.json()["detail"]


def test_delete_virtual_key():
    """Delete a virtual key permanently."""
    # Create
    create_resp = client.post("/v1/keys", json={"name": "delete-test"})
    key_id = create_resp.json()["key"]["key_id"]

    # Delete
    resp = client.delete(f"/v1/keys/{key_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # Should be gone
    resp2 = client.post("/v1/keys/validate", headers={"Authorization": f"Bearer {key_id}"})
    assert resp2.status_code == 403


def test_validate_virtual_key_success():
    """Validate a valid, active key with budget remaining."""
    create_resp = client.post("/v1/keys", json={"name": "valid-test", "budget_usd": 100.0})
    key_id = create_resp.json()["key"]["key_id"]

    resp = client.post("/v1/keys/validate", headers={"Authorization": f"Bearer {key_id}"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_validate_missing_key():
    """Validation fails with no Authorization header."""
    resp = client.post("/v1/keys/validate")
    assert resp.status_code == 401


def test_validate_invalid_key():
    """Validation fails with a non-existent key."""
    resp = client.post("/v1/keys/validate", headers={"Authorization": "Bearer sk-router-nonexistent"})
    assert resp.status_code == 403
    assert "Invalid" in resp.json()["detail"]


def test_virtual_key_budget_enforcement():
    """Budget-exhausted keys should be rejected."""
    from app.main import _vk_manager

    create_resp = client.post("/v1/keys", json={"name": "budget-test", "budget_usd": 0.01})
    key_id = create_resp.json()["key"]["key_id"]

    # Simulate spending beyond budget
    _vk_manager.record_spend(key_id, 0.02)

    resp = client.post("/v1/keys/validate", headers={"Authorization": f"Bearer {key_id}"})
    assert resp.status_code == 403
    assert "Budget exhausted" in resp.json()["detail"]


def test_virtual_key_rate_limit():
    """Rate-limited keys should be rejected after exceeding RPM."""
    from app.main import _vk_manager

    create_resp = client.post("/v1/keys", json={
        "name": "ratelimit-test",
        "rate_limit_rpm": 2,  # Very low limit for testing
    })
    key_id = create_resp.json()["key"]["key_id"]

    # First two requests should succeed
    for _ in range(2):
        resp = client.post("/v1/keys/validate", headers={"Authorization": f"Bearer {key_id}"})
        assert resp.status_code == 200

    # Third should be rate-limited
    resp = client.post("/v1/keys/validate", headers={"Authorization": f"Bearer {key_id}"})
    assert resp.status_code == 403
    assert "Rate limit" in resp.json()["detail"]
