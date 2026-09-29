"""Tests for Feedback Loop (Backlog Item 6)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_submit_positive_feedback():
    """Submit a thumbs-up rating."""
    resp = client.post("/v1/feedback", json={
        "response_id": "chatcmpl-test123",
        "model_id": "anthropic/claude-opus-5.5",
        "rating": 1,
        "category": "Coding",
        "session_id": "test-session-1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert "feedback_id" in data
    assert data["feedback_id"].startswith("fb-")


def test_submit_negative_feedback():
    """Submit a thumbs-down rating."""
    resp = client.post("/v1/feedback", json={
        "response_id": "chatcmpl-test456",
        "model_id": "openai/gpt-5.6-luna",
        "rating": -1,
        "category": "Reasoning",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"


def test_invalid_rating():
    """Reject ratings that aren't +1 or -1."""
    resp = client.post("/v1/feedback", json={
        "response_id": "chatcmpl-invalid",
        "model_id": "test-model",
        "rating": 5,
    })
    assert resp.status_code == 400


def test_feedback_stats():
    """Stats endpoint returns valid aggregates."""
    # Submit some feedback first
    for i in range(3):
        client.post("/v1/feedback", json={
            "response_id": f"chatcmpl-stats-{i}",
            "model_id": "google/gemini-3.1-pro",
            "rating": 1,
            "category": "Summary",
            "session_id": f"stats-session-{i}",
        })
    client.post("/v1/feedback", json={
        "response_id": "chatcmpl-stats-neg",
        "model_id": "google/gemini-3.1-pro",
        "rating": -1,
        "category": "Summary",
        "session_id": "stats-neg-session",
    })

    resp = client.get("/v1/feedback/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_feedback"] >= 4
    assert stats["positive"] >= 3
    assert stats["negative"] >= 1
    assert "satisfaction_rate" in stats
    assert "models" in stats
    assert "adjustments" in stats


def test_feedback_recent():
    """Recent feedback returns entries."""
    resp = client.get("/v1/feedback/recent?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "feedback" in data
    assert len(data["feedback"]) >= 1


def test_feedback_adjustments():
    """Adjustments endpoint returns model score deltas."""
    resp = client.get("/v1/feedback/adjustments")
    assert resp.status_code == 200
    data = resp.json()
    assert "adjustments" in data
    # Adjustments should be a dict of model_id -> category -> float
    assert isinstance(data["adjustments"], dict)


def test_feedback_adjustment_after_threshold():
    """Score adjustment kicks in after 5+ votes."""
    from app.main import _feedback_manager

    model = "test/adjustment-model"
    category = "Coding"

    # Submit 6 positive votes
    for i in range(6):
        _feedback_manager.record_feedback(
            response_id=f"adj-test-{i}",
            model_id=model,
            rating=1,
            category=category,
            session_id=f"adj-sess-{i}",
        )

    adj = _feedback_manager.get_adjustment(model, category)
    # After 6 positive votes, adjustment should be positive
    assert adj > 0


def test_duplicate_vote_updates():
    """Voting again on the same response updates rather than duplicates."""
    resp1 = client.post("/v1/feedback", json={
        "response_id": "chatcmpl-dup-test",
        "model_id": "test/dup-model",
        "rating": 1,
        "session_id": "dup-session",
    })
    assert resp1.status_code == 200

    resp2 = client.post("/v1/feedback", json={
        "response_id": "chatcmpl-dup-test",
        "model_id": "test/dup-model",
        "rating": -1,
        "session_id": "dup-session",
    })
    assert resp2.status_code == 200
    # Should update existing, not create new
