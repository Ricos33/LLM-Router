"""
Feedback Loop — collect user feedback (👍/👎) on responses and use it to
adjust classifier fit scores over time.

Storage: SQLite table `feedback` in the metrics database.
Anti-abuse: rate-limit feedback per session/IP, require valid response_id.

The fit score adjustment uses exponential weighted averaging:
- Each vote contributes a delta proportional to 1/sqrt(total_votes) for that model
- Positive votes increase the model's score for the detected category
- Negative votes decrease it
- Minimum 5 votes before adjustments take effect (noise floor)
"""

import json
import sqlite3
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class FeedbackEntry:
    feedback_id: str
    response_id: str
    model_id: str
    category: str        # e.g. "Coding", "Reasoning"
    rating: int          # +1 (thumbs up) or -1 (thumbs down)
    timestamp: float
    session_id: Optional[str] = None


class FeedbackManager:
    """Collect and aggregate user feedback on model responses."""

    def __init__(self, db_path: str = "./data/metrics.sqlite3"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_table()

        # In-memory aggregated scores: model_id -> category -> adjustment
        self._score_adjustments: Dict[str, Dict[str, float]] = {}
        self._vote_counts: Dict[str, Dict[str, int]] = {}  # model -> category -> count
        self._load_aggregates()

    def _get_conn(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    response_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    rating INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    session_id TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_model
                ON feedback(model_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_response
                ON feedback(response_id)
            """)
            conn.commit()
        finally:
            conn.close()

    def _load_aggregates(self) -> None:
        """Load aggregated feedback from database on startup."""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT model_id, category,
                       SUM(rating) as net_rating,
                       COUNT(*) as vote_count
                FROM feedback
                GROUP BY model_id, category
            """).fetchall()

            for row in rows:
                model_id = row["model_id"]
                category = row["category"]
                net_rating = row["net_rating"]
                vote_count = row["vote_count"]

                if model_id not in self._score_adjustments:
                    self._score_adjustments[model_id] = {}
                    self._vote_counts[model_id] = {}

                self._vote_counts[model_id][category] = vote_count
                # Adjustment: net_rating / sqrt(vote_count), scaled to small delta
                import math
                if vote_count >= 5:
                    adj = (net_rating / math.sqrt(vote_count)) * 0.02
                    self._score_adjustments[model_id][category] = max(-0.15, min(0.15, adj))
                else:
                    self._score_adjustments[model_id][category] = 0.0
        finally:
            conn.close()

    def record_feedback(
        self,
        response_id: str,
        model_id: str,
        rating: int,
        category: str = "general",
        session_id: Optional[str] = None,
    ) -> FeedbackEntry:
        """Record a feedback vote."""
        import uuid
        feedback_id = f"fb-{uuid.uuid4().hex[:12]}"
        now = time.time()

        # Anti-abuse: max 10 votes per session in the last minute
        if session_id:
            conn = self._get_conn()
            try:
                recent = conn.execute(
                    "SELECT COUNT(*) as cnt FROM feedback WHERE session_id = ? AND timestamp > ?",
                    (session_id, now - 60.0),
                ).fetchone()
                if recent and recent["cnt"] >= 10:
                    raise ValueError("Rate limit: too many feedback submissions")
            finally:
                conn.close()

        # Prevent duplicate voting on same response
        conn = self._get_conn()
        try:
            existing = conn.execute(
                "SELECT feedback_id FROM feedback WHERE response_id = ? AND session_id = ?",
                (response_id, session_id or ""),
            ).fetchone()
            if existing:
                # Update existing vote
                conn.execute(
                    "UPDATE feedback SET rating = ?, timestamp = ? WHERE feedback_id = ?",
                    (rating, now, existing["feedback_id"]),
                )
                conn.commit()
                entry = FeedbackEntry(
                    feedback_id=existing["feedback_id"],
                    response_id=response_id,
                    model_id=model_id,
                    category=category,
                    rating=rating,
                    timestamp=now,
                    session_id=session_id,
                )
            else:
                entry = FeedbackEntry(
                    feedback_id=feedback_id,
                    response_id=response_id,
                    model_id=model_id,
                    category=category,
                    rating=rating,
                    timestamp=now,
                    session_id=session_id,
                )
                conn.execute(
                    "INSERT INTO feedback (feedback_id, response_id, model_id, category, rating, timestamp, session_id) VALUES (?,?,?,?,?,?,?)",
                    (entry.feedback_id, entry.response_id, entry.model_id, entry.category, entry.rating, entry.timestamp, entry.session_id or ""),
                )
                conn.commit()
        finally:
            conn.close()

        # Recalculate adjustment for this model+category
        self._recalculate(model_id, category)

        return entry

    def _recalculate(self, model_id: str, category: str) -> None:
        """Recalculate score adjustment for a model+category."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT SUM(rating) as net, COUNT(*) as cnt FROM feedback WHERE model_id = ? AND category = ?",
                (model_id, category),
            ).fetchone()
            if not row:
                return

            net = row["net"] or 0
            cnt = row["cnt"] or 0

            with self._lock:
                if model_id not in self._score_adjustments:
                    self._score_adjustments[model_id] = {}
                    self._vote_counts[model_id] = {}

                self._vote_counts[model_id][category] = cnt

                import math
                if cnt >= 5:
                    adj = (net / math.sqrt(cnt)) * 0.02
                    self._score_adjustments[model_id][category] = max(-0.15, min(0.15, adj))
                else:
                    self._score_adjustments[model_id][category] = 0.0
        finally:
            conn.close()

    def get_adjustment(self, model_id: str, category: str) -> float:
        """Get the feedback-based score adjustment for a model+category."""
        with self._lock:
            return self._score_adjustments.get(model_id, {}).get(category, 0.0)

    def get_all_adjustments(self) -> Dict[str, Dict[str, float]]:
        """Get all feedback adjustments."""
        with self._lock:
            return dict(self._score_adjustments)

    def get_stats(self) -> dict:
        """Get feedback statistics."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) as cnt FROM feedback").fetchone()["cnt"]
            positive = conn.execute("SELECT COUNT(*) as cnt FROM feedback WHERE rating > 0").fetchone()["cnt"]
            negative = conn.execute("SELECT COUNT(*) as cnt FROM feedback WHERE rating < 0").fetchone()["cnt"]

            # Per-model summary
            models = conn.execute("""
                SELECT model_id,
                       COUNT(*) as votes,
                       SUM(CASE WHEN rating > 0 THEN 1 ELSE 0 END) as positive,
                       SUM(CASE WHEN rating < 0 THEN 1 ELSE 0 END) as negative
                FROM feedback
                GROUP BY model_id
                ORDER BY votes DESC
            """).fetchall()

            model_stats = [
                {
                    "model_id": r["model_id"],
                    "total_votes": r["votes"],
                    "positive": r["positive"],
                    "negative": r["negative"],
                    "satisfaction_rate": round(r["positive"] / r["votes"], 3) if r["votes"] > 0 else 0.0,
                }
                for r in models
            ]

            return {
                "total_feedback": total,
                "positive": positive,
                "negative": negative,
                "satisfaction_rate": round(positive / total, 3) if total > 0 else 0.0,
                "models": model_stats,
                "adjustments": self.get_all_adjustments(),
            }
        finally:
            conn.close()

    def get_recent(self, limit: int = 50) -> List[dict]:
        """Get recent feedback entries."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM feedback ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
