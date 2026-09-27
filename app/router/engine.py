import time
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from app.config import settings
from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    RouterMetadata,
)
from app.classifier import (
    BaseClassifier,
    ClassificationResult,
    ModelTier,
    RuleBasedClassifier,
    JevClassifier,
)
from app.backends import BaseBackend, OllamaBackend, OpenAICompatibleBackend
from app.storage import MetricsTracker, RequestMetric

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    tier: ModelTier
    model_name: str
    backend: BaseBackend
    provider_name: str
    classifier_score: float
    reasons: List[str]


class RouterEngine:
    """
    Core engine managing classification, policy decisions, backend dispatch,
    cost accounting, and real-time metric logging.
    """

    def __init__(
        self,
        classifier: Optional[BaseClassifier] = None,
        cheap_backend: Optional[BaseBackend] = None,
        frontier_backend: Optional[BaseBackend] = None,
        metrics_tracker: Optional[MetricsTracker] = None,
    ):
        # 1. Classifier setup
        if classifier:
            self.classifier = classifier
        elif settings.classifier_mode == "jev":
            self.classifier = JevClassifier(
                api_key=settings.jev_api_key,
                base_url=settings.jev_api_base_url,
            )
        else:
            self.classifier = RuleBasedClassifier(
                threshold=settings.classifier_confidence_threshold
            )

        # 2. Backends setup
        self.cheap_backend = cheap_backend or OllamaBackend(
            base_url=settings.cheap_api_base_url,
            default_model=settings.cheap_model,
            simulate_fallback=settings.simulate_fallback,
        )

        self.frontier_backend = frontier_backend or OpenAICompatibleBackend(
            base_url=settings.frontier_api_base_url,
            api_key=settings.frontier_api_key,
            default_model=settings.frontier_model,
            simulate_fallback=settings.simulate_fallback,
        )

        # 3. Metrics persistence
        self.metrics = metrics_tracker or MetricsTracker(
            db_path=str(settings.db_path)
        )

    def decide_route(
        self, request: ChatCompletionRequest, tier_header_override: Optional[str] = None
    ) -> RoutingDecision:
        """
        Evaluate request against explicit policy overrides and the classifier.
        """
        # Rule 1: Header override (e.g. X-Router-Tier: frontier / cheap)
        if tier_header_override:
            tier_clean = tier_header_override.strip().lower()
            if tier_clean in ("frontier", "pro", "high"):
                return RoutingDecision(
                    tier=ModelTier.FRONTIER,
                    model_name=settings.frontier_model,
                    backend=self.frontier_backend,
                    provider_name=settings.frontier_provider,
                    classifier_score=1.0,
                    reasons=["Explicit override via 'X-Router-Tier' header (Frontier)"],
                )
            elif tier_clean in ("cheap", "local", "low"):
                return RoutingDecision(
                    tier=ModelTier.CHEAP,
                    model_name=settings.cheap_model,
                    backend=self.cheap_backend,
                    provider_name=settings.cheap_provider,
                    classifier_score=0.0,
                    reasons=["Explicit override via 'X-Router-Tier' header (Cheap)"],
                )

        # Rule 2: Model name override in request payload
        req_model = (request.model or "").strip().lower()
        if req_model in ("router-frontier", "frontier", settings.frontier_model.lower()):
            return RoutingDecision(
                tier=ModelTier.FRONTIER,
                model_name=settings.frontier_model,
                backend=self.frontier_backend,
                provider_name=settings.frontier_provider,
                classifier_score=1.0,
                reasons=[f"Explicit model target requested: {request.model}"],
            )
        elif req_model in ("router-cheap", "cheap", settings.cheap_model.lower()):
            return RoutingDecision(
                tier=ModelTier.CHEAP,
                model_name=settings.cheap_model,
                backend=self.cheap_backend,
                provider_name=settings.cheap_provider,
                classifier_score=0.0,
                reasons=[f"Explicit model target requested: {request.model}"],
            )

        # Rule 3: Intelligent classification
        classification: ClassificationResult = self.classifier.classify(request.messages)

        if classification.tier == ModelTier.FRONTIER:
            return RoutingDecision(
                tier=ModelTier.FRONTIER,
                model_name=settings.frontier_model,
                backend=self.frontier_backend,
                provider_name=settings.frontier_provider,
                classifier_score=classification.score,
                reasons=classification.reasons,
            )
        else:
            return RoutingDecision(
                tier=ModelTier.CHEAP,
                model_name=settings.cheap_model,
                backend=self.cheap_backend,
                provider_name=settings.cheap_provider,
                classifier_score=classification.score,
                reasons=classification.reasons,
            )

    async def route_and_execute(
        self, request: ChatCompletionRequest, tier_header_override: Optional[str] = None
    ) -> ChatCompletionResponse:
        start_time = time.perf_counter()

        # Step 1: Decision
        decision = self.decide_route(request, tier_header_override)

        # Step 2: Execution via selected backend
        response = await decision.backend.complete(request, model_override=decision.model_name)

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Step 3: Cost calculation
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

        # Cost if handled by frontier
        cost_frontier = (
            (prompt_tokens / 1_000_000.0) * settings.frontier_prompt_price_per_m
            + (completion_tokens / 1_000_000.0) * settings.frontier_completion_price_per_m
        )

        # Actual cost
        if decision.tier == ModelTier.FRONTIER:
            cost_actual = cost_frontier
        else:
            cost_actual = (
                (prompt_tokens / 1_000_000.0) * settings.cheap_prompt_price_per_m
                + (completion_tokens / 1_000_000.0) * settings.cheap_completion_price_per_m
            )

        cost_saved = max(0.0, cost_frontier - cost_actual)

        # Step 4: Record metadata
        router_metadata = RouterMetadata(
            routed_tier=decision.tier.value,
            classifier_score=decision.classifier_score,
            classifier_reasons=decision.reasons,
            actual_model=decision.model_name,
            upstream_provider=decision.provider_name,
            latency_ms=latency_ms,
            cost_actual_usd=round(cost_actual, 6),
            cost_frontier_usd=round(cost_frontier, 6),
            cost_saved_usd=round(cost_saved, 6),
        )
        response.router_metadata = router_metadata

        # Step 5: Log to persistent metrics SQLite store
        prompt_preview = request.messages[-1].content if request.messages else "empty"
        metric = RequestMetric(
            timestamp=time.time(),
            prompt_preview=prompt_preview,
            routed_tier=decision.tier.value,
            model_used=decision.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            cost_actual=cost_actual,
            cost_if_frontier=cost_frontier,
            cost_saved=cost_saved,
            classifier_score=decision.classifier_score,
            classifier_reasons=decision.reasons,
        )
        self.metrics.record_request(metric)

        return response
