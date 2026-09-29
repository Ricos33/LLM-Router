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
from app.router.response_cache import global_response_cache
from app.backends import (
    AnthropicBackend,
    BaseBackend,
    OllamaBackend,
    OpenAICompatibleBackend,
    AgyBackend,
)
from app.storage import MetricsTracker, RequestMetric
from app.catalog import CURATED_MODELS, get_model_by_id, get_model_pricing, get_model_cache_pricing
from app.router.circuit_breaker import ProviderCircuitBreaker
from app.router.rules import RoutingRuleManager
from app.router.budget import BudgetManager

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    tier: ModelTier
    model_name: str
    backend: BaseBackend
    provider_name: str
    classifier_score: float
    reasons: List[str]
    matched_rule: Optional[str] = None


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

        # 4. Resilience Circuit Breaker
        self.circuit_breaker = ProviderCircuitBreaker(
            failure_threshold=3, cooldown_seconds=30.0
        )

        # 5. Enterprise Routing Rules Manager
        self.rules_manager = RoutingRuleManager()

        # 6. Enterprise Budget Alert Manager
        thresholds_list = []
        if getattr(settings, "budget_alert_thresholds", None):
            try:
                thresholds_list = [float(x.strip()) for x in settings.budget_alert_thresholds.split(",") if x.strip()]
            except Exception:
                thresholds_list = [50.0, 80.0, 90.0, 100.0]
        self.budget_manager = BudgetManager(
            webhook_url=getattr(settings, "budget_alert_webhook_url", ""),
            thresholds=thresholds_list or [50.0, 80.0, 90.0, 100.0],
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

    def _build_classification_candidates(self, strategy: str) -> List[Dict[str, Any]]:
        """Shortlist catalog models for per-model Jev evaluation.

        Picks up to 2 models per tier (cheap/medium/frontier) so Jev can
        score each candidate's fit against its own profile (pricing, context
        window, benchmarks) instead of answering generic tier questions.
        """
        try:
            shortlist: List[Any] = []
            by_tier: Dict[str, List[Any]] = {}
            for m in CURATED_MODELS:
                tier = str(getattr(m, "tier", "") or "").lower()
                # Normalize enum-ish values ("ModelTier.FRONTIER", "frontier") 
                tier = tier.split(".")[-1]
                by_tier.setdefault(tier, []).append(m)
            for tier in ("cheap", "medium", "frontier"):
                shortlist.extend(by_tier.get(tier, [])[:2])
            return [m.model_dump() for m in shortlist[:6]]
        except Exception:
            logger.warning("Failed to build classification candidates", exc_info=True)
            return []

    def decide_route(
        self,
        request: ChatCompletionRequest,
        tier_header_override: Optional[str] = None,
        strategy_override: Optional[str] = None,
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

        # Check if explicit curated catalog model was requested
        catalog_model = get_model_by_id(req_model)
        if catalog_model and req_model not in ("router-auto", "auto", ""):
            tier_val = catalog_model.tier or "medium"
            tier_enum = ModelTier(tier_val) if tier_val in [t.value for t in ModelTier] else ModelTier.MEDIUM
            backend = self.cheap_backend if tier_enum == ModelTier.CHEAP else self.frontier_backend
            score = 1.0 if tier_enum == ModelTier.FRONTIER else 0.5 if tier_enum == ModelTier.MEDIUM else 0.1
            return RoutingDecision(
                tier=tier_enum,
                model_name=catalog_model.id,
                backend=backend,
                provider_name=catalog_model.provider or "unknown",
                classifier_score=score,
                reasons=[f"Explicit curated model requested: {catalog_model.id} ({tier_val} tier)"],
            )

        # Rule 2.5: Custom & Enterprise Routing Rules Policy
        rule_match = self.rules_manager.evaluate(request.messages)
        if rule_match:
            target_tier_str = (rule_match.target_tier or "medium").lower()
            tier_enum = ModelTier(target_tier_str) if target_tier_str in [t.value for t in ModelTier] else ModelTier.MEDIUM
            
            if settings.agy_enabled:
                target_model = self.agy_backend.get_model_for_tier(target_tier_str)
                target_provider = "agy"
                backend = self.agy_backend
            else:
                target_model = rule_match.target_model or (
                    settings.cheap_model if tier_enum == ModelTier.CHEAP else settings.frontier_model
                )
                target_provider = rule_match.target_provider or (
                    settings.cheap_provider if tier_enum == ModelTier.CHEAP else settings.frontier_provider
                )
                backend = self.cheap_backend if tier_enum == ModelTier.CHEAP else self.frontier_backend

            score = 1.0 if tier_enum == ModelTier.FRONTIER else (0.5 if tier_enum == ModelTier.MEDIUM else 0.1)

            return RoutingDecision(
                tier=tier_enum,
                model_name=target_model,
                backend=backend,
                provider_name=target_provider,
                classifier_score=score,
                reasons=[f"Routing policy rule '{rule_match.rule_name}' applied: {rule_match.reason}"],
                matched_rule=rule_match.rule_id,
            )

        # Rule 3: Intelligent classification
        strategy = strategy_override or getattr(request, "strategy", "balanced") or "balanced"
        candidates = self._build_classification_candidates(strategy)
        classification: ClassificationResult = self.classifier.classify(
            request.messages, strategy=strategy, candidates=candidates
        )

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

    def get_fallback_candidates(self, primary_decision: RoutingDecision) -> List[RoutingDecision]:
        """
        Generate an ordered fallback chain for resilience:
        1. Same-tier alternative models from different providers.
        2. Escalation to frontier models if primary was cheap or medium.
        3. Default configured backend (guaranteed simulation fallback if needed).
        """
        candidates: List[RoutingDecision] = []

        # 1. Same-tier alternatives from catalog
        same_tier = [
            m for m in CURATED_MODELS
            if m.tier == primary_decision.tier.value and m.id != primary_decision.model_name
        ]
        for alt in same_tier[:2]:
            backend = self.cheap_backend if primary_decision.tier == ModelTier.CHEAP else self.frontier_backend
            candidates.append(RoutingDecision(
                tier=primary_decision.tier,
                model_name=alt.id,
                backend=backend,
                provider_name=alt.provider or "unknown",
                classifier_score=primary_decision.classifier_score,
                reasons=[f"Same-tier fallback candidate: {alt.id}"],
            ))

        # 2. Frontier escalation if primary was cheap or medium
        if primary_decision.tier != ModelTier.FRONTIER:
            frontier_models = [
                m for m in CURATED_MODELS
                if m.tier == "frontier" and m.id != primary_decision.model_name
            ]
            for f_alt in frontier_models[:2]:
                candidates.append(RoutingDecision(
                    tier=ModelTier.FRONTIER,
                    model_name=f_alt.id,
                    backend=self.frontier_backend,
                    provider_name=f_alt.provider or settings.frontier_provider,
                    classifier_score=1.0,
                    reasons=[f"Escalation to frontier fallback: {f_alt.id}"],
                ))

        # 3. Default configured backend (guaranteed simulation fallback if needed)
        default_frontier = RoutingDecision(
            tier=ModelTier.FRONTIER,
            model_name=self.frontier_backend.default_model,
            backend=self.frontier_backend,
            provider_name=settings.frontier_provider,
            classifier_score=1.0,
            reasons=["Default frontier backend fallback"],
        )
        if not any(c.model_name == default_frontier.model_name for c in candidates):
            candidates.append(default_frontier)

        # Prioritize candidates from healthy/available providers over tripped ones
        candidates.sort(
            key=lambda c: 0 if self.circuit_breaker.is_available(c.provider_name) else 1
        )

        return candidates

    async def route_and_execute(
        self,
        request: ChatCompletionRequest,
        tier_header_override: Optional[str] = None,
        strategy_override: Optional[str] = None,
    ) -> ChatCompletionResponse:
        start_time = time.perf_counter()

        # Step 0: Gateway Semantic/Exact Cache Check
        if settings.gateway_cache_enabled:
            cached_resp = global_response_cache.get(request)
            if cached_resp:
                latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
                if cached_resp.router_metadata:
                    cached_resp.router_metadata.gateway_cache_hit = True
                    cached_resp.router_metadata.latency_ms = latency_ms
                    # Cost is 0 for cached queries
                    cached_resp.router_metadata.cost_actual_usd = 0.0
                    # The cost_saved is whatever it would have cost on frontier + the actual cost saved
                    cached_resp.router_metadata.cost_saved_usd = cached_resp.router_metadata.cost_frontier_usd
                logger.info("Gateway Cache HIT for request.")
                return cached_resp

        # Step 0b: Budget check
        current_cost = self.metrics.get_current_month_cost()
        self.budget_manager.check_and_notify(current_cost, settings.monthly_budget_usd)
        if settings.monthly_budget_usd > 0:
            if current_cost >= settings.monthly_budget_usd:
                from fastapi import HTTPException
                raise HTTPException(status_code=429, detail=f"Monthly budget of ${settings.monthly_budget_usd:.2f} exceeded.")

        # Step 1: Decision
        decision = self.decide_route(
            request,
            tier_header_override=tier_header_override,
            strategy_override=strategy_override,
        )

        # Enforce Request Budget Cap (prevent runaway costs on massive prompts)
        if settings.max_cost_per_request_usd > 0.0 and decision.tier == ModelTier.FRONTIER:
            est_tokens = sum(len(m.content) for m in request.messages) / 4.0
            price_in, _ = get_model_pricing(decision.model_name)
            est_cost = (est_tokens / 1_000_000.0) * (price_in or settings.frontier_prompt_price_per_m)
            if est_cost > settings.max_cost_per_request_usd:
                logger.warning(f"Estimated prompt cost ${est_cost:.4f} exceeds max ${settings.max_cost_per_request_usd:.2f}. Downgrading to MEDIUM tier.")
                decision = self.decide_route(
                    request,
                    tier_header_override="medium",
                    strategy_override=strategy_override,
                )
                if decision.reasons:
                    decision.reasons.append(f"Auto-downgraded from Frontier: estimated prompt cost ${est_cost:.4f} > limit ${settings.max_cost_per_request_usd:.2f}")

        # Step 2: Execution via selected backend with automatic resilient fallback chain
        attempt_queue = [decision] + self.get_fallback_candidates(decision)
        executed_decision = decision
        response = None
        fallback_history: List[str] = []
        fallback_triggered = False

        for idx, candidate in enumerate(attempt_queue):
            try:
                # Execution request copy for safe truncation
                exec_req = request.model_copy()
                exec_req.messages = list(request.messages)
                
                if settings.auto_truncate_context:
                    m_info = get_model_by_id(candidate.model_name)
                    if m_info and m_info.context_length:
                        # Simple heuristic token estimation (chars / 4)
                        # We keep the first message (usually system prompt) if possible
                        max_ctx = m_info.context_length - (exec_req.max_tokens or 1000)
                        
                        def est_tokens(msgs):
                            return sum(len(m.content) for m in msgs) / 4
                        
                        if est_tokens(exec_req.messages) > max_ctx and len(exec_req.messages) > 1:
                            sys_msg = [exec_req.messages[0]] if exec_req.messages[0].role == "system" else []
                            rest = exec_req.messages[1:] if exec_req.messages[0].role == "system" else exec_req.messages[:]
                            
                            while rest and est_tokens(sys_msg + rest) > max_ctx:
                                rest.pop(0) # drop oldest
                            exec_req.messages = sys_msg + rest
                            logger.info(f"Auto-truncated prompt for {candidate.model_name} to fit {m_info.context_length} window")

                api_key_override = (
                    getattr(request, "provider_keys", None).get(candidate.provider_name.lower())
                    if getattr(request, "provider_keys", None) and candidate.provider_name
                    else None
                )
                
                # Gateway Provider Key Pool Rotation (Load Balancing & Rate Limit Avoidance)
                if not api_key_override:
                    pool = ""
                    if candidate.tier == ModelTier.FRONTIER:
                        pool = settings.frontier_api_keys_pool
                    
                    if pool:
                        import random
                        keys = [k.strip() for k in pool.split(",") if k.strip()]
                        if keys:
                            api_key_override = random.choice(keys)
                            logger.info(f"Rotated API key via {candidate.tier.value} pool for {candidate.provider_name}")
                response = await candidate.backend.complete(
                    exec_req,
                    model_override=candidate.model_name,
                    api_key_override=api_key_override,
                )
                executed_decision = candidate
                self.circuit_breaker.record_success(candidate.provider_name)
                if idx > 0:
                    fallback_triggered = True
                    fallback_history.append(f"{candidate.model_name} (succeeded)")
                    logger.info(f"Fallback succeeded on attempt {idx + 1} with {candidate.model_name}")
                break
            except Exception as e:
                self.circuit_breaker.record_failure(candidate.provider_name, str(e))
                err_msg = str(e)[:60]
                fallback_history.append(f"{candidate.model_name} (failed: {err_msg})")
                logger.warning(
                    f"Execution attempt {idx + 1} ({candidate.model_name}) failed: {e}. Retrying with next fallback."
                )

        if response is None:
            raise RuntimeError(f"All {len(attempt_queue)} model execution attempts failed: {fallback_history}")

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        self.circuit_breaker.record_latency(executed_decision.provider_name, latency_ms)

        # Step 3: Cost calculation
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

        # Baseline cost if handled by frontier
        cost_frontier = (
            (prompt_tokens / 1_000_000.0) * settings.frontier_prompt_price_per_m
            + (completion_tokens / 1_000_000.0) * settings.frontier_completion_price_per_m
        )

        # Actual cost depending on provider and tier
        price_in, price_out = get_model_pricing(executed_decision.model_name)
        if price_in > 0 or price_out > 0:
            cost_actual = (
                (prompt_tokens / 1_000_000.0) * price_in
                + (completion_tokens / 1_000_000.0) * price_out
            )
        elif executed_decision.provider_name == "agy":
            cost_actual = (
                (prompt_tokens / 1_000_000.0) * settings.agy_prompt_price_per_m
                + (completion_tokens / 1_000_000.0) * settings.agy_completion_price_per_m
            )
        elif executed_decision.tier == ModelTier.FRONTIER:
            cost_actual = cost_frontier
        elif executed_decision.tier == ModelTier.MEDIUM:
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

        # Step 3b: Prompt caching economics estimate (assuming 80% prefix cache hit)
        price_cache_read = get_model_cache_pricing(executed_decision.model_name)
        cost_cached = None
        cache_savings_pct = None
        if price_cache_read is not None and prompt_tokens > 0:
            cached_in = prompt_tokens * 0.8
            uncached_in = prompt_tokens * 0.2
            cost_cached = (
                (cached_in / 1_000_000.0) * price_cache_read
                + (uncached_in / 1_000_000.0) * (price_in or 0.0)
                + (completion_tokens / 1_000_000.0) * (price_out or 0.0)
            )
            if cost_actual > 0:
                cache_savings_pct = round(max(0.0, (cost_actual - cost_cached) / cost_actual * 100), 1)

        # Step 4: Record metadata
        circuit_status = self.circuit_breaker.get_health_status().get(
            executed_decision.provider_name.lower(), {}
        ).get("status", "healthy")

        strat_used = strategy_override or getattr(request, "strategy", "balanced") or "balanced"
        router_metadata = RouterMetadata(
            routed_tier=executed_decision.tier.value,
            classifier_score=executed_decision.classifier_score,
            classifier_reasons=executed_decision.reasons,
            actual_model=executed_decision.model_name,
            upstream_provider=executed_decision.provider_name,
            latency_ms=latency_ms,
            cost_actual_usd=round(cost_actual, 6),
            cost_frontier_usd=round(cost_frontier, 6),
            cost_saved_usd=round(cost_saved, 6),
            cost_cached_usd=round(cost_cached, 6) if cost_cached is not None else None,
            cache_savings_pct=cache_savings_pct,
            fallback_triggered=fallback_triggered,
            fallback_chain=fallback_history,
            circuit_status=circuit_status,
            routing_strategy=strat_used,
            matched_rule=executed_decision.matched_rule,
        )
        response.router_metadata = router_metadata

        # Step 5: Log to persistent metrics SQLite store
        prompt_preview = request.messages[-1].content if request.messages else "empty"
        metric = RequestMetric(
            timestamp=time.time(),
            prompt_preview=prompt_preview,
            routed_tier=executed_decision.tier.value,
            model_used=executed_decision.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
            cost_actual=cost_actual,
            cost_if_frontier=cost_frontier,
            cost_saved=cost_saved,
            classifier_score=executed_decision.classifier_score,
            classifier_reasons=executed_decision.reasons,
        )
        self.metrics.record_request(metric)

        # Notify if newly recorded cost trips a budget threshold
        if settings.monthly_budget_usd > 0:
            new_cost = self.metrics.get_current_month_cost()
            self.budget_manager.check_and_notify(new_cost, settings.monthly_budget_usd)

        # Cache the successful response if enabled
        if settings.gateway_cache_enabled and not request.stream:
            global_response_cache.set(request, response)

        return response
