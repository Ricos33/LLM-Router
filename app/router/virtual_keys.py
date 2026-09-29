"""
Virtual API Keys — issue per-application/team keys (sk-router-...) with
independent budgets and rate limits.  Real provider keys stay hidden server-side.

Storage: SQLite (same DB as metrics) for persistence across restarts.
"""

import hashlib
import json
import secrets
import sqlite3
import time
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional


# ── Data model ──────────────────────────────────────────────────────────────

@dataclass
class VirtualKey:
    key_id: str                        # e.g. "sk-router-abc123..."
    name: str                          # Human-readable label ("frontend-team")
    created_at: float = 0.0
    budget_usd: float = 100.0          # Monthly spending limit
    spent_usd: float = 0.0             # Current month spend
    rate_limit_rpm: int = 60           # Requests per minute
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)   # Arbitrary tags

    def to_dict(self) -> dict:
        d = asdict(self)
        # Mask the key in listings (show first 12 chars)
        d["key_preview"] = self.key_id[:16] + "..." if len(self.key_id) > 16 else self.key_id
        return d


# ── Rate limiter (sliding window) ──────────────────────────────────────────

class _RateLimiter:
    """Simple in-memory sliding-window rate limiter per key."""

    def __init__(self):
        self._windows: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check_and_record(self, key_id: str, rpm_limit: int) -> bool:
        """Return True if allowed, False if rate-limited."""
        now = time.time()
        window_start = now - 60.0

        with self._lock:
            timestamps = self._windows.get(key_id, [])
            # Prune old entries
            timestamps = [t for t in timestamps if t > window_start]

            if len(timestamps) >= rpm_limit:
                self._windows[key_id] = timestamps
                return False

            timestamps.append(now)
            self._windows[key_id] = timestamps
            return True

    def clear(self, key_id: str) -> None:
        with self._lock:
            self._windows.pop(key_id, None)


# ── Key manager ─────────────────────────────────────────────────────────────

class VirtualKeyManager:
    """CRUD + enforcement for virtual API keys."""

    def __init__(self, db_path: str = "./data/metrics.sqlite3"):
        self.db_path = db_path
        self._rate_limiter = _RateLimiter()
        self._ensure_table()

    def _get_conn(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS virtual_keys (
                    key_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    budget_usd REAL DEFAULT 100.0,
                    spent_usd REAL DEFAULT 0.0,
                    rate_limit_rpm INTEGER DEFAULT 60,
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ── CRUD ────────────────────────────────────────────────────────────

    def create_key(self, name: str, budget_usd: float = 100.0, rate_limit_rpm: int = 60, metadata: Optional[Dict] = None) -> VirtualKey:
        """Issue a new virtual API key."""
        raw = secrets.token_hex(24)
        key_id = f"sk-router-{raw}"
        now = time.time()
        vk = VirtualKey(
            key_id=key_id,
            name=name,
            created_at=now,
            budget_usd=budget_usd,
            spent_usd=0.0,
            rate_limit_rpm=rate_limit_rpm,
            is_active=True,
            metadata=metadata or {},
        )
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO virtual_keys (key_id, name, created_at, budget_usd, spent_usd, rate_limit_rpm, is_active, metadata) VALUES (?,?,?,?,?,?,?,?)",
                (vk.key_id, vk.name, vk.created_at, vk.budget_usd, vk.spent_usd, vk.rate_limit_rpm, 1, json.dumps(vk.metadata)),
            )
            conn.commit()
        finally:
            conn.close()
        return vk

    def list_keys(self) -> List[VirtualKey]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM virtual_keys ORDER BY created_at DESC").fetchall()
            return [self._row_to_key(r) for r in rows]
        finally:
            conn.close()

    def get_key(self, key_id: str) -> Optional[VirtualKey]:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM virtual_keys WHERE key_id = ?", (key_id,)).fetchone()
            if row:
                return self._row_to_key(row)
            return None
        finally:
            conn.close()

    def revoke_key(self, key_id: str) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.execute("UPDATE virtual_keys SET is_active = 0 WHERE key_id = ?", (key_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def delete_key(self, key_id: str) -> bool:
        conn = self._get_conn()
        try:
            cur = conn.execute("DELETE FROM virtual_keys WHERE key_id = ?", (key_id,))
            conn.commit()
            self._rate_limiter.clear(key_id)
            return cur.rowcount > 0
        finally:
            conn.close()

    def record_spend(self, key_id: str, cost_usd: float) -> None:
        """Record cost against a virtual key's budget."""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE virtual_keys SET spent_usd = spent_usd + ? WHERE key_id = ?", (cost_usd, key_id))
            conn.commit()
        finally:
            conn.close()

    def reset_monthly_spend(self) -> None:
        """Reset all spend counters (call at month boundary)."""
        conn = self._get_conn()
        try:
            conn.execute("UPDATE virtual_keys SET spent_usd = 0.0")
            conn.commit()
        finally:
            conn.close()

    # ── Enforcement ─────────────────────────────────────────────────────

    def validate_request(self, key_id: str) -> tuple[bool, str]:
        """Validate a virtual key before allowing a request.

        Returns (allowed: bool, reason: str).
        """
        vk = self.get_key(key_id)
        if vk is None:
            return False, "Invalid API key"
        if not vk.is_active:
            return False, "API key has been revoked"
        if vk.spent_usd >= vk.budget_usd:
            return False, f"Budget exhausted (${vk.spent_usd:.2f} / ${vk.budget_usd:.2f})"
        if not self._rate_limiter.check_and_record(key_id, vk.rate_limit_rpm):
            return False, f"Rate limit exceeded ({vk.rate_limit_rpm} RPM)"
        return True, "ok"

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_key(row: sqlite3.Row) -> VirtualKey:
        meta = {}
        try:
            meta = json.loads(row["metadata"]) if row["metadata"] else {}
        except Exception:
            pass
        return VirtualKey(
            key_id=row["key_id"],
            name=row["name"],
            created_at=row["created_at"],
            budget_usd=row["budget_usd"],
            spent_usd=row["spent_usd"],
            rate_limit_rpm=row["rate_limit_rpm"],
            is_active=bool(row["is_active"]),
            metadata=meta,
        )
