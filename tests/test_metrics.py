import os
import tempfile
import pytest
from app.storage import MetricsTracker, RequestMetric


def test_metrics_tracker_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, "test_metrics.sqlite3")
        tracker = MetricsTracker(db_path=db_file)

        initial = tracker.get_summary()
        assert initial["total_requests"] == 0

        # Record a cheap request
        metric1 = RequestMetric(
            timestamp=1000.0,
            prompt_preview="Short greeting",
            routed_tier="cheap",
            model_used="llama3.2:3b",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            latency_ms=45.0,
            cost_actual=0.00001,
            cost_if_frontier=0.00020,
            cost_saved=0.00019,
            classifier_score=0.15,
            classifier_reasons=["greeting pattern"]
        )
        row_id = tracker.record_request(metric1)
        assert row_id == 1

        # Record a frontier request
        metric2 = RequestMetric(
            timestamp=1001.0,
            prompt_preview="Complex code architecture",
            routed_tier="frontier",
            model_used="gpt-4o",
            prompt_tokens=100,
            completion_tokens=300,
            total_tokens=400,
            latency_ms=250.0,
            cost_actual=0.005,
            cost_if_frontier=0.005,
            cost_saved=0.0,
            classifier_score=0.85,
            classifier_reasons=["code detected", "high complexity"]
        )
        tracker.record_request(metric2)

        summary = tracker.get_summary()
        assert summary["total_requests"] == 2
        assert summary["cheap_requests"] == 1
        assert summary["frontier_requests"] == 1
        assert summary["cheap_percentage"] == 50.0
        assert summary["total_cost_saved"] > 0

        recent = tracker.get_recent_requests(limit=10)
        assert len(recent) == 2
        assert recent[0]["model_used"] == "gpt-4o"
        assert recent[1]["model_used"] == "llama3.2:3b"
