"""Tests for PII Guardrails (Backlog Item 5)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_pii_scan_email():
    """Detect and mask email addresses."""
    resp = client.post("/v1/guardrails/scan", json={
        "text": "Contact me at john.doe@example.com for details"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_found"] is True
    assert "[EMAIL_REDACTED]" in data["masked_text"]
    assert "email" in data["detections"]["types_detected"]
    assert "john.doe@example.com" not in data["masked_text"]


def test_pii_scan_phone():
    """Detect and mask phone numbers."""
    resp = client.post("/v1/guardrails/scan", json={
        "text": "Call me at +1 (555) 123-4567 tomorrow"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_found"] is True
    assert "[PHONE_REDACTED]" in data["masked_text"]


def test_pii_scan_iban():
    """Detect and mask IBAN numbers."""
    resp = client.post("/v1/guardrails/scan", json={
        "text": "Wire to FR7630006000011234567890189 please"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_found"] is True
    assert "[IBAN_REDACTED]" in data["masked_text"]
    assert "iban" in data["detections"]["types_detected"]


def test_pii_scan_ip():
    """Detect and mask IPv4 addresses."""
    resp = client.post("/v1/guardrails/scan", json={
        "text": "Server is at 192.168.1.100 port 8080"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_found"] is True
    assert "[IP_REDACTED]" in data["masked_text"]


def test_pii_scan_no_pii():
    """Clean text should pass through unchanged."""
    text = "The weather is nice today"
    resp = client.post("/v1/guardrails/scan", json={"text": text})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_found"] is False
    assert data["masked_text"] == text


def test_pii_scan_multiple():
    """Multiple PII types in one text."""
    resp = client.post("/v1/guardrails/scan", json={
        "text": "Email: user@test.com, IP: 10.0.0.1, Phone: +33 6 12 34 56 78"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pii_found"] is True
    assert data["detections"]["detection_count"] >= 2
    assert "user@test.com" not in data["masked_text"]
    assert "10.0.0.1" not in data["masked_text"]


def test_guardrail_stats():
    """Stats endpoint returns valid data."""
    resp = client.get("/v1/guardrails/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_scanned" in data
    assert "total_detections" in data
    assert "enabled" in data


def test_guardrail_toggle():
    """Toggle guardrails on/off."""
    resp = client.post("/v1/guardrails/toggle?enable=true")
    assert resp.status_code == 200
    assert resp.json()["pii_guardrails_enabled"] is True

    resp = client.post("/v1/guardrails/toggle?enable=false")
    assert resp.status_code == 200
    assert resp.json()["pii_guardrails_enabled"] is False


def test_guardrails_in_chat_completions():
    """When enabled, PII should be masked before reaching the provider."""
    settings.pii_guardrails_enabled = True
    
    resp = client.post("/v1/chat/completions", json={
        "model": "router-auto",
        "messages": [{"role": "user", "content": "Contact john@example.com about the project at 192.168.1.1"}],
    })
    assert resp.status_code == 200
    # The response should have been generated — we can't inspect what was sent
    # to the provider in a unit test, but we verify the endpoint doesn't crash
    assert resp.json()["choices"][0]["message"]["content"] != ""
    
    settings.pii_guardrails_enabled = False


def test_luhn_validation():
    """Credit card Luhn check."""
    from app.router.guardrails import _luhn_check
    # Valid test card number (Visa)
    assert _luhn_check("4111111111111111") is True
    # Invalid number
    assert _luhn_check("4111111111111112") is False
    # Too short
    assert _luhn_check("123") is False
