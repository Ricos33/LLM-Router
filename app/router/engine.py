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
from app.backends import (
    AnthropicBackend,
    BaseBackend,
    OllamaBackend,
    OpenAICompatibleBackend,
    AgyBackend,
)
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
        agy_backend: Optional[BaseBackend] = None,
        metrics_tracker: Optional[MetricsTracker] = None,
    ):
        # 1. Classifier setup
        if classifier:
            self.classifier = classifier
        elif settings.classifier_mode == "jev":
            if not settings.jev_api_key:
                logger.warning(
                    "CLASSIFIER_MODE is 'jev' but JEV_API_KEY is not configured. "
                    "JevClassifier will fall back to rule-based mock classification."
                )
            self.classifier = JevClassifier(
                api_key=settings.jev_api_key,
                base_url=settings.jev_api_base_url,
                model=settings.jev_model,
                timeout=settings.jev_timeout,
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

        self.agy_backend = agy_backend or AgyBackend(
            binary_path=settings.agy_binary_path,
            tier_map=settings.agy_tier_map,
            timeout=settings.agy_timeout,
            simulate_fallback=settings.simulate_fallback,
        )

        # 3. Metrics persistence
        self.metrics = metrics_tracker or MetricsTracker(
            db_path=str(settings.db_path)
        )

    def get_tier_models(self) -> Dict[str, Dict[str, Any]]:
        """
        Return the resolved models and metadata for each tier based on backend settings.
        Provides the real model names (e.g. gemini-3.8-flash-low, gemini-3.1-pro-high, claude-opus-4-6-thinking).
        """
        if settings.agy_enabled and hasattr(self, "agy_backend"):
            return {
                "cheap": {
                    "tier": "cheap",
                    "model": self.agy_backend.get_model_for_tier("cheap"),
                    "provider": "agy",
                    "effort": self.agy_backend.get_tier_config("cheap").get("effort", "low"),
                    "displayName": "Flash / Local Fast",
                    "description": "Idéal pour requêtes légères, salutations et faits simples",
                },
                "medium": {
                    "tier": "medium",
                    "model": self.agy_backend.get_model_for_tier("medium"),
                    "provider": "agy",
                    "effort": self.agy_backend.get_tier_config("medium").get("effort", "high"),
                    "displayName": "Pro Intermediate",
                    "description": "Pour tâches structurées, refactorings et scripts standards",
                },
                "frontier": {
                    "tier": "frontier",
                    "model": self.agy_backend.get_model_for_tier("frontier"),
                    "provider": "agy",
                    "effort": self.agy_backend.get_tier_config("frontier").get("effort"),
                    "displayName": "Frontier Intelligence",
                    "description": "Raisonnement complexe, architecture et code critique",
                },
            }
        else:
            cheap_model = (
                settings.agy_tier_map.get("cheap", {}).get("model")
                if "cheap" in settings.agy_tier_map
                else settings.cheap_model
            ) or settings.cheap_model
            medium_model = (
                settings.agy_tier_map.get("medium", {}).get("model")
                if "medium" in settings.agy_tier_map
                else "gemini-3.1-pro-high"
            )
            frontier_model = (
                settings.agy_tier_map.get("frontier", {}).get("model")
                if "frontier" in settings.agy_tier_map
                else settings.frontier_model
            ) or settings.frontier_model

            return {
                "cheap": {
                    "tier": "cheap",
                    "model": cheap_model,
                    "provider": "agy" if "cheap" in settings.agy_tier_map else settings.cheap_provider,
                    "effort": settings.agy_tier_map.get("cheap", {}).get("effort", "low"),
                    "displayName": "Flash / Local Fast",
                    "description": "Idéal pour requêtes légères, salutations et faits simples",
                },
                "medium": {
                    "tier": "medium",
                    "model": medium_model,
                    "provider": "agy" if "medium" in settings.agy_tier_map else "intermediate",
                    "effort": settings.agy_tier_map.get("medium", {}).get("effort", "high"),
                    "displayName": "Pro Intermediate",
                    "description": "Pour tâches structurées, refactorings et scripts standards",
                },
                "frontier": {
                    "tier": "frontier",
                    "model": frontier_model,
                    "provider": "agy" if "frontier" in settings.agy_tier_map else settings.frontier_provider,
                    "effort": settings.agy_tier_map.get("frontier", {}).get("effort"),
                    "displayName": "Frontier Intelligence",
                    "description": "Raisonnement complexe, architecture et code critique",
                },
            }

    def decide_route(
        self, request: ChatCompletionRequest, tier_header_override: Optional[str] = None
    ) -> RoutingDecision:
        """
        Evaluate request against explicit policy overrides and the classifier.
        """
        # Rule 1: Header override (e.g. X-Router-Tier: frontier / medium / cheap)
        if tier_header_override:
            tier_clean = tier_header_override.strip().lower()
            if tier_clean in ("frontier", "high"):
                if settings.agy_enabled:
                    model = self.agy_backend.get_model_for_tier("frontier")
                    return RoutingDecision(
                        tier=ModelTier.FRONTIER,
                        model_name=model,
                        backend=self.agy_backend,
                        provider_name="agy",
                        classifier_score=1.0,
                        reasons=["Explicit override via 'X-Router-Tier' header (Frontier - Agy)"],
                    )
                return RoutingDecision(
                    tier=ModelTier.FRONTIER,
                    model_name=self.frontier_backend.default_model,
                    backend=self.frontier_backend,
                    provider_name=settings.frontier_provider,
                    classifier_score=1.0,
                    reasons=["Explicit override via 'X-Router-Tier' header (Frontier)"],
                )
            elif tier_clean in ("medium", "pro", "mid"):
                if settings.agy_enabled:
                    model = self.agy_backend.get_model_for_tier("medium")
                    return RoutingDecision(
                        tier=ModelTier.MEDIUM,
                        model_name=model,
                        backend=self.agy_backend,
                        provider_name="agy",
                        classifier_score=0.5,
                        reasons=["Explicit override via 'X-Router-Tier' header (Medium - Agy)"],
                    )
                return RoutingDecision(
                    tier=ModelTier.MEDIUM,
                    model_name=self.frontier_backend.default_model,
                    backend=self.frontier_backend,
                    provider_name=settings.frontier_provider,
                    classifier_score=0.5,
                    reasons=["Explicit override via 'X-Router-Tier' header (Medium)"],
                )
            elif tier_clean in ("cheap", "local", "low"):
                if settings.agy_enabled:
                    model = self.agy_backend.get_model_for_tier("cheap")
                    return RoutingDecision(
                        tier=ModelTier.CHEAP,
                        model_name=model,
                        backend=self.agy_backend,
                        provider_name="agy",
                        classifier_score=0.0,
                        reasons=["Explicit override via 'X-Router-Tier' header (Cheap - Agy)"],
                    )
                return RoutingDecision(
                    tier=ModelTier.CHEAP,
                    model_name=self.cheap_backend.default_model,
                    backend=self.cheap_backend,
                    provider_name=settings.cheap_provider,
                    classifier_score=0.0,
                    reasons=["Explicit override via 'X-Router-Tier' header (Cheap)"],
                )

        # Rule 2: Model name override in request payload
        req_model = (request.model or "").strip().lower()

        # Check explicit Agy aliases or targets
        if req_model in ("agy-frontier", "router-agy-frontier"):
            model = self.agy_backend.get_model_for_tier("frontier")
            return RoutingDecision(
                tier=ModelTier.FRONTIER,
                model_name=model,
                backend=self.agy_backend,
                provider_name="agy",
                classifier_score=1.0,
                reasons=[f"Explicit model target requested: {request.model}"],
            )
        elif req_model in ("agy-medium", "router-agy-medium", "router-medium", "medium"):
            model = self.agy_backend.get_model_for_tier("medium") if (settings.agy_enabled or "agy" in req_model) else settings.frontier_model
            backend = self.agy_backend if (settings.agy_enabled or "agy" in req_model) else self.frontier_backend
            provider = "agy" if (settings.agy_enabled or "agy" in req_model) else settings.frontier_provider
            return RoutingDecision(
                tier=ModelTier.MEDIUM,
                model_name=model,
                backend=backend,
                provider_name=provider,
                classifier_score=0.5,
                reasons=[f"Explicit model target requested: {request.model}"],
            )
        elif req_model in ("agy-cheap", "router-agy-cheap"):
            model = self.agy_backend.get_model_for_tier("cheap")
            return RoutingDecision(
                tier=ModelTier.CHEAP,
                model_name=model,
                backend=self.agy_backend,
                provider_name="agy",
                classifier_score=0.0,
                reasons=[f"Explicit model target requested: {request.model}"],
            )
        elif req_model in ("router-frontier", "frontier", settings.frontier_model.lower(), settings.openai_model.lower(), settings.anthropic_model.lower()):
            if settings.agy_enabled:
                model = self.agy_backend.get_model_for_tier("frontier")
                return RoutingDecision(
                    tier=ModelTier.FRONTIER,
                    model_name=model,
                    backend=self.agy_backend,
                    provider_name="agy",
                    classifier_score=1.0,
                    reasons=[f"Explicit model target requested: {request.model} (routed to Agy)"],
                )
            return RoutingDecision(
                tier=ModelTier.FRONTIER,
                model_name=self.frontier_backend.default_model,
                backend=self.frontier_backend,
                provider_name=settings.frontier_provider,
                classifier_score=1.0,
                reasons=[f"Explicit model target requested: {request.model}"],
            )
        elif req_model in ("router-cheap", "cheap", settings.cheap_model.lower()):
            if settings.agy_enabled:
                model = self.agy_backend.get_model_for_tier("cheap")
                return RoutingDecision(
                    tier=ModelTier.CHEAP,
                    model_name=model,
                    backend=self.agy_backend,
                    provider_name="agy",
                    classifier_score=0.0,
                    reasons=[f"Explicit model target requested: {request.model} (routed to Agy)"],
                )
            return RoutingDecision(
                tier=ModelTier.CHEAP,
                model_name=self.cheap_backend.default_model,
                backend=self.cheap_backend,
                provider_name=settings.cheap_provider,
                classifier_score=0.0,
                reasons=[f"Explicit model target requested: {request.model}"],
            )

        # Check if direct agy model was requested
        agy_tier = self.agy_backend.get_tier_for_model(req_model)
        if agy_tier:
            tier_enum = ModelTier(agy_tier) if agy_tier in [t.value for t in ModelTier] else ModelTier.CHEAP
            return RoutingDecision(
                tier=tier_enum,
                model_name=req_model,
                backend=self.agy_backend,
                provider_name="agy",
                classifier_score=1.0 if agy_tier == "frontier" else 0.5 if agy_tier == "medium" else 0.0,
                reasons=[f"Explicit Agy model target requested: {request.model}"],
            )

        # Rule 3: Intelligent classification
        classification: ClassificationResult = self.classifier.classify(request.messages)

        if settings.agy_enabled:
            if classification.tier == ModelTier.FRONTIER:
                model = self.agy_backend.get_model_for_tier("frontier")
                tier_enum = ModelTier.FRONTIER
            elif classification.tier == ModelTier.MEDIUM:
                model = self.agy_backend.get_model_for_tier("medium")
                tier_enum = ModelTier.MEDIUM
            else:
                model = self.agy_backend.get_model_for_tier("cheap")
                tier_enum = ModelTier.CHEAP

            return RoutingDecision(
                tier=tier_enum,
                model_name=model,
                backend=self.agy_backend,
                provider_name="agy",
                classifier_score=classification.score,
                reasons=classification.reasons,
            )

        if classification.tier == ModelTier.FRONTIER:
            return RoutingDecision(
                tier=ModelTier.FRONTIER,
                model_name=self.frontier_backend.default_model,
                backend=self.frontier_backend,
                provider_name=settings.frontier_provider,
                classifier_score=classification.score,
                reasons=classification.reasons,
            )
        elif classification.tier == ModelTier.MEDIUM:
            return RoutingDecision(
                tier=ModelTier.MEDIUM,
                model_name=self.frontier_backend.default_model,
                backend=self.frontier_backend,
                provider_name=settings.frontier_provider,
                classifier_score=classification.score,
                reasons=classification.reasons,
            )
        else:
            return RoutingDecision(
                tier=ModelTier.CHEAP,
                model_name=self.cheap_backend.default_model,
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

        # Step 2: Execution via selected backend with automatic fallback
        try:
            response = await decision.backend.complete(request, model_override=decision.model_name)
        except Exception as e:
            logger.warning(f"Backend execution failed for {decision.tier.value} ({decision.model_name}): {e}. Falling back to FRONTIER tier.")
            # Fallback to Frontier
            decision = RoutingDecision(
                tier=ModelTier.FRONTIER,
                model_name=self.frontier_backend.default_model,
                backend=self.frontier_backend,
                provider_name=settings.frontier_provider,
                classifier_score=decision.classifier_score,
                reasons=decision.reasons + [f"Fallback triggered due to failure in {decision.model_name}"]
            )
            response = await decision.backend.complete(request, model_override=decision.model_name)

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Step 3: Cost calculation
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

        # Baseline cost if handled by frontier
        cost_frontier = (
            (prompt_tokens / 1_000_000.0) * settings.frontier_prompt_price_per_m
            + (completion_tokens / 1_000_000.0) * settings.frontier_completion_price_per_m
        )

        # Actual cost depending on provider and tier
        if decision.provider_name == "agy":
            cost_actual = (
                (prompt_tokens / 1_000_000.0) * settings.agy_prompt_price_per_m
                + (completion_tokens / 1_000_000.0) * settings.agy_completion_price_per_m
            )
        elif decision.tier == ModelTier.FRONTIER:
            cost_actual = cost_frontier
        elif decision.tier == ModelTier.MEDIUM:
            cost_actual = (
                (prompt_tokens / 1_000_000.0) * settings.medium_prompt_price_per_m
                + (completion_tokens / 1_000_000.0) * settings.medium_completion_price_per_m
            )
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
