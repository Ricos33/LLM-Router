import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProviderCircuitBreaker:
    """
    Production circuit breaker tracking health and consecutive failures per provider.
    Prevents cascading timeouts and automatically steers traffic away from failing backends.
    
    States:
    - HEALTHY: normal operation (0 to failure_threshold - 1 failures)
    - DEGRADED: sporadic errors detected, but still passing probe traffic
    - TRIPPED: threshold reached, traffic diverted to alternatives during cooldown window
    """

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._providers: Dict[str, Dict[str, Any]] = {}

    def _get_or_create(self, provider: str) -> Dict[str, Any]:
        p = provider.strip().lower()
        if p not in self._providers:
            self._providers[p] = {
                "consecutive_failures": 0,
                "total_failures": 0,
                "total_successes": 0,
                "last_failure_time": None,
                "last_success_time": None,
                "last_error": None,
                "status": "healthy",
            }
        return self._providers[p]

    def record_success(self, provider: str) -> None:
        """Record successful completion, resetting consecutive failures to zero."""
        data = self._get_or_create(provider)
        data["consecutive_failures"] = 0
        data["total_successes"] += 1
        data["last_success_time"] = time.time()
        data["status"] = "healthy"
        data["last_error"] = None

    def record_failure(self, provider: str, error_message: str) -> None:
        """Record provider error and trip circuit if consecutive threshold exceeded."""
        data = self._get_or_create(provider)
        data["consecutive_failures"] += 1
        data["total_failures"] += 1
        data["last_failure_time"] = time.time()
        data["last_error"] = error_message[:120]

        if data["consecutive_failures"] >= self.failure_threshold:
            data["status"] = "tripped"
            logger.warning(
                f"Circuit breaker TRIPPED for provider '{provider}' "
                f"after {data['consecutive_failures']} consecutive errors: {error_message}"
            )
        else:
            data["status"] = "degraded"

    def is_available(self, provider: str) -> bool:
        """
        Check if provider is available to receive requests.
        Returns False only if status is TRIPPED and cooldown window is still active.
        """
        data = self._get_or_create(provider)
        if data["status"] != "tripped":
            return True

        # Check if cooldown has elapsed (Half-Open probe)
        last_failure = data.get("last_failure_time") or 0
        elapsed = time.time() - last_failure
        if elapsed >= self.cooldown_seconds:
            logger.info(
                f"Circuit breaker cooldown elapsed ({elapsed:.1f}s) for provider '{provider}'. "
                "Allowing half-open probe request."
            )
            data["status"] = "degraded"
            return True

        return False

    def get_health_status(self) -> Dict[str, Any]:
        """Return health telemetry dictionary for all tracked providers."""
        now = time.time()
        result = {}
        for p, d in self._providers.items():
            last_fail = d.get("last_failure_time")
            in_cooldown = False
            remaining_cooldown = 0.0
            if d["status"] == "tripped" and last_fail:
                elapsed = now - last_fail
                if elapsed < self.cooldown_seconds:
                    in_cooldown = True
                    remaining_cooldown = round(self.cooldown_seconds - elapsed, 1)

            result[p] = {
                "status": d["status"],
                "available": not in_cooldown,
                "consecutive_failures": d["consecutive_failures"],
                "total_successes": d["total_successes"],
                "total_failures": d["total_failures"],
                "last_error": d["last_error"],
                "remaining_cooldown_seconds": remaining_cooldown if in_cooldown else 0.0,
            }
        return result

    def trip_provider(self, provider: str, reason: str = "Simulated outage via Chaos Controller") -> Dict[str, Any]:
        """Manually trip circuit breaker for chaos resilience simulation."""
        data = self._get_or_create(provider)
        data["consecutive_failures"] = self.failure_threshold
        data["total_failures"] += 1
        data["last_failure_time"] = time.time()
        data["last_error"] = f"[Chaos Simulation] {reason[:100]}"
        data["status"] = "tripped"
        logger.warning(f"Chaos simulation: Circuit breaker manually TRIPPED for provider '{provider}'")
        return self.get_health_status().get(provider.strip().lower(), {})

    def reset_provider(self, provider: str) -> Dict[str, Any]:
        """Manually reset a provider's circuit breaker to healthy."""
        data = self._get_or_create(provider)
        data["consecutive_failures"] = 0
        data["last_failure_time"] = None
        data["last_error"] = None
        data["status"] = "healthy"
        logger.info(f"Circuit breaker manually RESET to healthy for provider '{provider}'")
        return self.get_health_status().get(provider.strip().lower(), {})

    def reset_all(self) -> Dict[str, Any]:
        """Reset all tracked providers to healthy status."""
        for p in self._providers:
            self._providers[p]["consecutive_failures"] = 0
            self._providers[p]["last_failure_time"] = None
            self._providers[p]["last_error"] = None
            self._providers[p]["status"] = "healthy"
        logger.info("Circuit breaker: all providers manually reset to healthy.")
        return self.get_health_status()

