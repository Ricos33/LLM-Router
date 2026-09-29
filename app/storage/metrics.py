import json
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class RequestMetric:
    timestamp: float
    prompt_preview: str
    routed_tier: str
    model_used: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_actual: float
    cost_if_frontier: float
    cost_saved: float
    classifier_score: float
    classifier_reasons: List[str]


class MetricsTracker:
    def __init__(self, db_path: str = "./data/metrics.sqlite3"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    prompt_preview TEXT,
                    routed_tier TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    latency_ms REAL NOT NULL,
                    cost_actual REAL NOT NULL,
                    cost_if_frontier REAL NOT NULL,
                    cost_saved REAL NOT NULL,
                    classifier_score REAL NOT NULL,
                    classifier_reasons TEXT NOT NULL
                )
            """)
            conn.commit()

    def record_request(self, metric: RequestMetric) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO metrics (
                    timestamp, prompt_preview, routed_tier, model_used,
                    prompt_tokens, completion_tokens, total_tokens,
                    latency_ms, cost_actual, cost_if_frontier, cost_saved,
                    classifier_score, classifier_reasons
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.prompt_preview[:150],
                metric.routed_tier,
                metric.model_used,
                metric.prompt_tokens,
                metric.completion_tokens,
                metric.total_tokens,
                metric.latency_ms,
                metric.cost_actual,
                metric.cost_if_frontier,
                metric.cost_saved,
                metric.classifier_score,
                json.dumps(metric.classifier_reasons)
            ))
            conn.commit()
            return cursor.lastrowid

    def get_current_month_cost(self) -> float:
        import datetime
        now = datetime.datetime.now()
        start_of_month = datetime.datetime(now.year, now.month, 1).timestamp()
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COALESCE(SUM(cost_actual), 0.0)
                FROM metrics
                WHERE timestamp >= ?
            """, (start_of_month,))
            row = cur.fetchone()
            return row[0] if row else 0.0

    def get_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN routed_tier = 'cheap' THEN 1 ELSE 0 END) as cheap_requests,
                    SUM(CASE WHEN routed_tier = 'medium' THEN 1 ELSE 0 END) as medium_requests,
                    SUM(CASE WHEN routed_tier = 'frontier' THEN 1 ELSE 0 END) as frontier_requests,
                    COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
                    COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(cost_actual), 0.0) as total_cost_actual,
                    COALESCE(SUM(cost_if_frontier), 0.0) as total_cost_if_frontier,
                    COALESCE(SUM(cost_saved), 0.0) as total_cost_saved,
                    COALESCE(AVG(latency_ms), 0.0) as avg_latency_ms
                FROM metrics
            """)
            row = cur.fetchone()
            if not row or row["total_requests"] == 0:
                return {
                    "total_requests": 0,
                    "cheap_requests": 0,
                    "medium_requests": 0,
                    "frontier_requests": 0,
                    "cheap_percentage": 0.0,
                    "medium_percentage": 0.0,
                    "frontier_percentage": 0.0,
                    "tier_distribution": {
                        "cheap": 0,
                        "medium": 0,
                        "frontier": 0,
                    },
                    "total_tokens": 0,
                    "total_cost_actual": 0.0,
                    "total_cost_if_frontier": 0.0,
                    "total_cost_saved": 0.0,
                    "savings_percentage": 0.0,
                    "avg_latency_ms": 0.0,
                    "average_latency_ms": 0.0,
                    "total_errors": 0,
                    "current_month_cost": 0.0,
                    "monthly_budget_usd": getattr(__import__('app.config', fromlist=['settings']).settings, 'monthly_budget_usd', 0.0),
                }

            total = row["total_requests"]
            cost_if_frontier = row["total_cost_if_frontier"]
            cost_saved = row["total_cost_saved"]
            savings_pct = (cost_saved / cost_if_frontier * 100.0) if cost_if_frontier > 0 else 0.0

            cheap_cnt = row["cheap_requests"] or 0
            med_cnt = row["medium_requests"] or 0
            front_cnt = row["frontier_requests"] or 0
            avg_lat = round(row["avg_latency_ms"], 1)

            return {
                "total_requests": total,
                "cheap_requests": cheap_cnt,
                "medium_requests": med_cnt,
                "frontier_requests": front_cnt,
                "cheap_percentage": round(cheap_cnt / total * 100.0, 1),
                "medium_percentage": round(med_cnt / total * 100.0, 1),
                "frontier_percentage": round(front_cnt / total * 100.0, 1),
                "tier_distribution": {
                    "cheap": cheap_cnt,
                    "medium": med_cnt,
                    "frontier": front_cnt,
                },
                "total_tokens": row["total_tokens"],
                "total_cost_actual": round(row["total_cost_actual"], 6),
                "total_cost_if_frontier": round(row["total_cost_if_frontier"], 6),
                "total_cost_saved": round(cost_saved, 6),
                "savings_percentage": round(savings_pct, 1),
                "avg_latency_ms": avg_lat,
                "average_latency_ms": avg_lat,
                "total_errors": 0,
                "current_month_cost": self.get_current_month_cost(),
                "monthly_budget_usd": getattr(__import__('app.config', fromlist=['settings']).settings, 'monthly_budget_usd', 0.0),
            }

    def get_recent_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, timestamp, prompt_preview, routed_tier, model_used,
                       prompt_tokens, completion_tokens, total_tokens,
                       latency_ms, cost_actual, cost_if_frontier, cost_saved,
                       classifier_score, classifier_reasons
                FROM metrics
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                # Provide camelCase and alternate names for seamless frontend compatibility
                item["actual_model"] = item["model_used"]
                item["cost_saved_usd"] = item["cost_saved"]
                try:
                    item["classifier_reasons"] = json.loads(item["classifier_reasons"])
                except Exception:
                    item["classifier_reasons"] = []
                results.append(item)
            return results

    def get_all_requests_csv(self) -> str:
        import csv
        import io
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, timestamp, prompt_preview, routed_tier, model_used,
                       prompt_tokens, completion_tokens, total_tokens,
                       latency_ms, cost_actual, cost_if_frontier, cost_saved,
                       classifier_score
                FROM metrics
                ORDER BY id DESC
            """)
            rows = cur.fetchall()
            output = io.StringIO()
            writer = csv.writer(output)
            # Write header
            writer.writerow([
                "id", "timestamp", "prompt_preview", "routed_tier", "model_used",
                "prompt_tokens", "completion_tokens", "total_tokens",
                "latency_ms", "cost_actual", "cost_if_frontier", "cost_saved", "classifier_score"
            ])
            for r in rows:
                writer.writerow([
                    r["id"], r["timestamp"], r["prompt_preview"], r["routed_tier"], r["model_used"],
                    r["prompt_tokens"], r["completion_tokens"], r["total_tokens"],
                    r["latency_ms"], r["cost_actual"], r["cost_if_frontier"], r["cost_saved"],
                    r["classifier_score"]
                ])
            return output.getvalue()

    def get_all_requests_json(self) -> str:
        """Export all request metrics as pretty-printed JSON."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, timestamp, prompt_preview, routed_tier, model_used,
                       prompt_tokens, completion_tokens, total_tokens,
                       latency_ms, cost_actual, cost_if_frontier, cost_saved,
                       classifier_score, classifier_reasons
                FROM metrics
                ORDER BY id DESC
            """)
            rows = [dict(r) for r in cur.fetchall()]
            for r in rows:
                try:
                    r["classifier_reasons"] = json.loads(r["classifier_reasons"])
                except Exception:
                    pass
            return json.dumps(rows, indent=2)



    def get_analytics(self) -> Dict[str, Any]:
        """Rich analytics: model distribution, avg scores per tier, top models, time-series."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # Model distribution
            cur.execute("""
                SELECT model_used, COUNT(*) as count, 
                       ROUND(AVG(cost_actual), 6) as avg_cost,
                       ROUND(AVG(latency_ms), 1) as avg_latency,
                       ROUND(AVG(classifier_score), 3) as avg_score
                FROM metrics
                GROUP BY model_used
                ORDER BY count DESC
            """)
            model_stats = [dict(r) for r in cur.fetchall()]

            # Tier distribution with avg classifier score
            cur.execute("""
                SELECT routed_tier, COUNT(*) as count,
                       ROUND(AVG(classifier_score), 3) as avg_score,
                       ROUND(AVG(cost_actual), 6) as avg_cost,
                       ROUND(SUM(cost_saved), 6) as total_saved
                FROM metrics
                GROUP BY routed_tier
            """)
            tier_stats = {r["routed_tier"]: dict(r) for r in cur.fetchall()}

            # Hourly time-series (last 24h)
            cur.execute("""
                SELECT 
                    CAST((timestamp / 3600) AS INTEGER) * 3600 as hour_ts,
                    COUNT(*) as requests,
                    ROUND(SUM(cost_actual), 6) as cost,
                    ROUND(SUM(cost_saved), 6) as saved
                FROM metrics
                WHERE timestamp > (strftime('%s', 'now') - 86400)
                GROUP BY hour_ts
                ORDER BY hour_ts
            """)
            hourly = [dict(r) for r in cur.fetchall()]

            # Cost efficiency score: % of requests routed to cheaper tiers
            cur.execute("SELECT COUNT(*) FROM metrics WHERE routed_tier != 'frontier'")
            non_frontier = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM metrics")
            total = cur.fetchone()[0]
            efficiency_pct = round((non_frontier / total * 100), 1) if total > 0 else 0

            # Upstream provider distribution
            provider_counts = {}
            for m_item in model_stats:
                m_name = m_item.get("model_used", "")
                p_name = m_name.split("/")[0] if "/" in m_name else "local/other"
                if p_name not in provider_counts:
                    provider_counts[p_name] = {
                        "provider": p_name,
                        "requests": 0,
                        "total_cost": 0.0,
                    }
                provider_counts[p_name]["requests"] += m_item.get("count", 0)
                provider_counts[p_name]["total_cost"] += round(float(m_item.get("avg_cost", 0.0)) * m_item.get("count", 0), 6)

            provider_stats = sorted(provider_counts.values(), key=lambda x: x["requests"], reverse=True)

            # Prompt cache economics analytics across all recorded prompt tokens
            cur.execute("SELECT SUM(prompt_tokens) FROM metrics")
            total_prompt_tokens = cur.fetchone()[0] or 0
            prompt_cache_savings_projected = round((total_prompt_tokens / 1_000_000.0) * 1.50 * 0.75 * 0.5, 6)

            prompt_cache_analytics = {
                "total_prompt_tokens": total_prompt_tokens,
                "projected_cache_savings_usd": prompt_cache_savings_projected,
                "provider_discounts": {
                    "anthropic": 90,
                    "deepseek": 90,
                    "qwen": 80,
                    "meta": 80,
                    "google": 75,
                    "xai": 75,
                    "openai": 50,
                    "mistral": 50,
                },
                "average_industry_discount_pct": 73.8,
            }

            return {
                "model_stats": model_stats,
                "tier_stats": tier_stats,
                "provider_stats": provider_stats,
                "prompt_cache_analytics": prompt_cache_analytics,
                "hourly_timeseries": hourly,
                "efficiency_percentage": efficiency_pct,
                "total_requests": total,
            }

    def clear_all(self) -> None:
        """Clear all metrics from the database."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM metrics")
            conn.commit()
