"""
Enterprise Budget and Threshold Alerting Engine.
Tracks monthly budget utilization, monitors threshold crossings (50%, 80%, 90%, 100%),
dispatches webhook notifications, and maintains alert history.
"""

import time
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class BudgetAlertEvent:
    def __init__(
        self,
        threshold_pct: float,
        current_cost: float,
        budget_limit: float,
        message: str,
        timestamp: Optional[float] = None,
    ):
        self.threshold_pct = threshold_pct
        self.current_cost = current_cost
        self.budget_limit = budget_limit
        self.message = message
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threshold_pct": self.threshold_pct,
            "current_cost": round(self.current_cost, 4),
            "budget_limit": round(self.budget_limit, 4),
            "message": self.message,
            "timestamp": self.timestamp,
        }


class BudgetManager:
    """
    Manages budget alerting thresholds and webhooks for the router gateway.
    """

    def __init__(
        self,
        webhook_url: str = "",
        thresholds: Optional[List[float]] = None,
    ):
        self.webhook_url = webhook_url
        self.thresholds = sorted(thresholds or [50.0, 80.0, 90.0, 100.0])
        self.fired_thresholds: set[float] = set()
        self.alert_history: List[BudgetAlertEvent] = []
        self._last_checked_month = time.strftime("%Y-%m")

    def _reset_if_new_month(self):
        current_month = time.strftime("%Y-%m")
        if current_month != self._last_checked_month:
            self._last_checked_month = current_month
            self.fired_thresholds.clear()

    def check_and_notify(self, current_cost: float, budget_limit: float) -> Optional[BudgetAlertEvent]:
        """
        Check if current cost crosses any un-fired alert thresholds.
        Returns the highest alert triggered in this check, if any.
        """
        self._reset_if_new_month()
        if budget_limit <= 0.0:
            return None

        pct_used = (current_cost / budget_limit) * 100.0
        last_alert = None

        for thresh in self.thresholds:
            if pct_used >= thresh and thresh not in self.fired_thresholds:
                self.fired_thresholds.add(thresh)
                severity = "CRITICAL" if thresh >= 100.0 else ("WARNING" if thresh >= 80.0 else "INFO")
                msg = f"[{severity}] Monthly budget alert: {pct_used:.1f}% used (${current_cost:.2f} of ${budget_limit:.2f})"
                alert = BudgetAlertEvent(
                    threshold_pct=thresh,
                    current_cost=current_cost,
                    budget_limit=budget_limit,
                    message=msg,
                )
                self.alert_history.append(alert)
                last_alert = alert
                logger.warning(msg)

                if self.webhook_url:
                    self._dispatch_webhook(alert)

        return last_alert

    def _dispatch_webhook(self, alert: BudgetAlertEvent) -> bool:
        if not self.webhook_url:
            return False
        try:
            with httpx.Client(timeout=4.0) as client:
                resp = client.post(
                    self.webhook_url,
                    json={
                        "event": "budget_threshold_alert",
                        "severity": "CRITICAL" if alert.threshold_pct >= 100 else ("WARNING" if alert.threshold_pct >= 80 else "INFO"),
                        "data": alert.to_dict(),
                    },
                )
                return resp.status_code < 400
        except Exception as e:
            logger.error(f"Failed to dispatch budget webhook to {self.webhook_url}: {e}")
            return False

    def trigger_test_alert(self, custom_webhook: Optional[str] = None) -> Dict[str, Any]:
        """
        Manually trigger a synthetic alert to verify webhook plumbing.
        """
        url_to_test = custom_webhook or self.webhook_url
        test_alert = BudgetAlertEvent(
            threshold_pct=80.0,
            current_cost=80.0,
            budget_limit=100.0,
            message="[TEST] Synthetic budget alert triggered from LLM Router console.",
        )
        self.alert_history.append(test_alert)
        dispatched = False
        dispatch_error = None

        if url_to_test:
            try:
                with httpx.Client(timeout=4.0) as client:
                    resp = client.post(
                        url_to_test,
                        json={
                            "event": "budget_test_alert",
                            "severity": "TEST",
                            "data": test_alert.to_dict(),
                        },
                    )
                    dispatched = resp.status_code < 400
                    if not dispatched:
                        dispatch_error = f"HTTP {resp.status_code}"
            except Exception as e:
                dispatch_error = str(e)

        return {
            "success": True,
            "alert": test_alert.to_dict(),
            "webhook_tested": bool(url_to_test),
            "webhook_dispatched": dispatched,
            "error": dispatch_error,
        }

    def get_status(self, current_cost: float, budget_limit: float) -> Dict[str, Any]:
        """
        Returns full diagnostic status of monthly budget utilization.
        """
        self._reset_if_new_month()
        if budget_limit <= 0.0:
            return {
                "monthly_budget_usd": 0.0,
                "current_cost_usd": round(current_cost, 4),
                "remaining_usd": None,
                "percent_used": 0.0,
                "status": "unlimited",
                "thresholds": self.thresholds,
                "webhook_configured": bool(self.webhook_url),
                "webhook_url": self.webhook_url if self.webhook_url else None,
                "alert_count": len(self.alert_history),
                "recent_alerts": [a.to_dict() for a in reversed(self.alert_history[-10:])],
            }

        pct = (current_cost / budget_limit) * 100.0
        remaining = max(0.0, budget_limit - current_cost)
        if pct >= 100.0:
            status = "critical"
        elif pct >= 80.0:
            status = "warning"
        elif pct >= 50.0:
            status = "caution"
        else:
            status = "normal"

        return {
            "monthly_budget_usd": round(budget_limit, 2),
            "current_cost_usd": round(current_cost, 4),
            "remaining_usd": round(remaining, 4),
            "percent_used": round(pct, 1),
            "status": status,
            "thresholds": self.thresholds,
            "webhook_configured": bool(self.webhook_url),
            "webhook_url": self.webhook_url if self.webhook_url else None,
            "alert_count": len(self.alert_history),
            "recent_alerts": [a.to_dict() for a in reversed(self.alert_history[-10:])],
        }

    def clear_alerts(self):
        """Clear recorded alerts and reset fired thresholds for manual testing."""
        self.fired_thresholds.clear()
        self.alert_history.clear()
