import httpx
import time
import logging
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.responses import StreamingResponse
import asyncio
import json
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from pydantic import BaseModel
from typing import List, Optional
class ClassifyRequest(BaseModel):
    messages: List[dict]
    budget: Optional[str] = "Any"
    providers: Optional[List[str]] = None
    strategy: Optional[str] = "balanced"

from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelListResponse,
    ModelObject,
    CompareRequest,
    CompareResponse,
    ModelCompareResult,
)
from app.catalog import CURATED_MODELS as _curated_models, MODEL_BENCHMARKS, get_model_by_id
from app.classifier.types import ClassificationResult
from app.router import RouterEngine

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("llm_router")

app = FastAPI(
    title="LLM-Router Gateway",
    description="Intelligent, OpenAI-compatible LLM Gateway routing queries to Cheap or Frontier models.",
    version="0.1.0",
)

# Enable CORS for Streamlit or client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate router engine
router_engine = RouterEngine()


@app.get("/health")
async def health_check():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": "llm-router",
        "classifier": settings.classifier_mode,
        "agy_enabled": settings.agy_enabled,
        "cheap_provider": settings.cheap_provider,
        "cheap_model": settings.cheap_model,
        "frontier_provider": settings.frontier_provider,
        "frontier_model": settings.frontier_model,
        "tier_models": router_engine.get_tier_models(),
    }



@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    models_with_scores = []
    for m in _curated_models:
        m_copy = m.model_copy()
        m_copy.scores = MODEL_BENCHMARKS.get(m.id, {"Reasoning": 0.8, "Coding": 0.8, "Summary": 0.8, "Creative": 0.8})
        models_with_scores.append(m_copy)
    return ModelListResponse(data=models_with_scores)
@app.get("/v1/models/tiers")
async def get_tier_models():
    """Retrieve configured tier-to-model mapping and metadata."""
    return router_engine.get_tier_models()


@app.get("/v1/providers/health")
async def get_providers_health():
    """Retrieve real-time circuit breaker and availability status for all providers."""
    return router_engine.circuit_breaker.get_health_status()


class ChaosTripRequest(BaseModel):
    provider: str
    reason: Optional[str] = "Simulated outage via Chaos Controller"


class ChaosResetRequest(BaseModel):
    provider: Optional[str] = "all"


@app.post("/v1/chaos/trip")
async def chaos_trip_provider(request: ChaosTripRequest):
    """
    Simulate a provider failure or outage by intentionally tripping its circuit breaker.
    Tests live resilient failover and alternative routing without breaking real services.
    """
    if not request.provider:
        raise HTTPException(status_code=400, detail="Provider name required")
    res = router_engine.circuit_breaker.trip_provider(
        request.provider,
        reason=request.reason or "Simulated outage via Chaos Controller"
    )
    return {
        "status": "tripped",
        "provider": request.provider.lower(),
        "provider_health": res,
        "all_health": router_engine.circuit_breaker.get_health_status()
    }


@app.post("/v1/chaos/reset")
async def chaos_reset_provider(request: Optional[ChaosResetRequest] = None):
    """
    Reset tripped circuit breakers back to healthy status.
    """
    target = (request.provider if request else "all") or "all"
    if target.lower() in ("all", "*"):
        router_engine.circuit_breaker.reset_all()
    else:
        router_engine.circuit_breaker.reset_provider(target)
    return {
        "status": "reset",
        "target": target,
        "all_health": router_engine.circuit_breaker.get_health_status()
    }


from app.router.response_cache import global_response_cache

@app.post("/v1/cache/clear", tags=["Gateway"])
async def clear_gateway_cache():
    """
    Clear the in-memory gateway semantic response cache.
    """
    global_response_cache.clear()
    return {"status": "ok", "message": "Gateway cache cleared"}


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    response: Response,
    x_router_tier: Optional[str] = Header(None, alias="X-Router-Tier"),
    x_router_strategy: Optional[str] = Header(None, alias="X-Router-Strategy"),
    x_provider_keys: Optional[str] = Header(None, alias="X-Provider-Keys"),
):
    """
    OpenAI-compatible chat completions endpoint.
    Dynamically routes queries based on prompt complexity or explicit overrides.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")
        
    if x_provider_keys:
        try:
            request.provider_keys = json.loads(x_provider_keys)
        except:
            pass

    try:
        completion = await router_engine.route_and_execute(
            request,
            tier_header_override=x_router_tier,
            strategy_override=x_router_strategy,
        )

        headers_dict = {}
        # Inject diagnostic routing headers
        if completion.router_metadata:
            meta = completion.router_metadata
            headers_dict["X-Router-Tier"] = meta.routed_tier
            headers_dict["X-Router-Model"] = meta.actual_model
            headers_dict["X-Router-Latency-MS"] = str(meta.latency_ms)
            headers_dict["X-Router-Saved-USD"] = str(meta.cost_saved_usd)
            headers_dict["X-Router-Score"] = str(meta.classifier_score)
            if meta.routing_strategy:
                headers_dict["X-Router-Strategy"] = meta.routing_strategy
            if meta.gateway_cache_hit:
                headers_dict["X-Gateway-Cache"] = "HIT"
            if meta.fallback_triggered:
                headers_dict["X-Router-Fallback"] = "true"
                headers_dict["X-Router-Fallback-Chain"] = "; ".join(meta.fallback_chain)
            
            for k, v in headers_dict.items():
                response.headers[k] = v

        if request.stream:
            async def stream_generator():
                content = completion.choices[0].message.content if completion.choices else ""
                response_id = completion.id
                model = completion.model
                
                # Initial role chunk
                first_chunk = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
                yield f"data: {json.dumps(first_chunk)}\n\n"
                
                # Content chunks (chunking dynamically by words)
                words = content.split(" ")
                for i in range(0, len(words), 3):
                    chunk_text = " ".join(words[i:i+3])
                    if i + 3 < len(words):
                        chunk_text += " "
                    chunk_payload = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": chunk_text}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(chunk_payload)}\n\n"
                    await asyncio.sleep(0.005)
                
                # Final chunk with usage stats
                final_chunk = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens,
                        "completion_tokens": completion.usage.completion_tokens,
                        "total_tokens": completion.usage.total_tokens,
                    }
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream", headers=headers_dict)

        return completion

    except Exception as e:
        logger.error(f"Routing completion failure: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM Router gateway error: {str(e)}")



@app.post("/v1/compare", response_model=CompareResponse)
async def compare_models(
    request: CompareRequest,
    x_provider_keys: Optional[str] = Header(None, alias="X-Provider-Keys"),
):
    """
    Compare multiple models side-by-side on the same prompt.
    Runs completions concurrently and calculates latency, token usage, and cost spread.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

    provider_keys = request.provider_keys or {}
    if x_provider_keys:
        try:
            provider_keys.update(json.loads(x_provider_keys))
        except Exception:
            pass

    # Determine models to compare
    target_models = request.models or []
    if not target_models:
        # Default: classify prompt and pick top 2 recommendations
        classify_req = ClassifyRequest(
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            budget="Any"
        )
        classification = await classify_prompt(classify_req)
        target_models = [r["model_id"] for r in (classification.recommendations or [])[:2]]

    if not target_models:
        target_models = [settings.cheap_model, settings.frontier_model]

    async def run_single(model_name: str) -> ModelCompareResult:
        sub_req = ChatCompletionRequest(
            model=model_name,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            response_format=request.response_format,
        )
        if provider_keys:
            sub_req.provider_keys = provider_keys

        start_t = time.perf_counter()
        try:
            resp = await router_engine.route_and_execute(sub_req)
            elapsed = (time.perf_counter() - start_t) * 1000.0
            content = resp.choices[0].message.content if resp.choices else ""
            meta = resp.router_metadata
            m_info = get_model_by_id(model_name)
            provider = m_info.provider if m_info else (meta.upstream_provider if meta else "unknown")
            tier = m_info.tier if m_info else (meta.routed_tier if meta else "medium")
            cost = meta.cost_actual_usd if meta else 0.0

            return ModelCompareResult(
                model=model_name,
                provider=provider,
                tier=tier,
                content=content,
                latency_ms=round(elapsed, 2),
                prompt_tokens=resp.usage.prompt_tokens,
                completion_tokens=resp.usage.completion_tokens,
                cost_usd=cost,
                gateway_cache_hit=meta.gateway_cache_hit if meta else False,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start_t) * 1000.0
            return ModelCompareResult(
                model=model_name,
                provider="unknown",
                tier="unknown",
                content="",
                latency_ms=round(elapsed, 2),
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=0.0,
                error=str(e),
            )

    results = await asyncio.gather(*[run_single(m) for m in target_models])

    valid_results = [r for r in results if not r.error]
    cheapest = min(valid_results, key=lambda x: x.cost_usd).model if valid_results else None
    fastest = min(valid_results, key=lambda x: x.latency_ms).model if valid_results else None
    min_cost = min((r.cost_usd for r in valid_results), default=0.0)
    max_cost = max((r.cost_usd for r in valid_results), default=0.0)

    prompt_text = request.messages[-1].content if request.messages else ""

    return CompareResponse(
        prompt=prompt_text,
        results=list(results),
        cheapest_model=cheapest,
        fastest_model=fastest,
        cost_spread_usd=round(max_cost - min_cost, 6),
    )


import hashlib
CLASSIFY_CACHE = {}

@app.post("/v1/classify", response_model=ClassificationResult)
async def classify_prompt(request: ClassifyRequest):
    """
    Classify a conversation to suggest an optimal model tier and return UI metadata.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")
        
    full_text = " ".join([m.get("content", "") for m in request.messages]).lower()
    strategy_val = (request.strategy or "balanced").lower().strip()
    cache_key = hashlib.md5(f"{full_text}_{request.budget}_{strategy_val}_{','.join(request.providers or [])}".encode()).hexdigest()
    
    if cache_key in CLASSIFY_CACHE:
        return CLASSIFY_CACHE[cache_key]
    
    # Run classifier
    from app.models import ChatMessage
    chat_msgs = [ChatMessage(**m) for m in request.messages]
    
    result = await router_engine.classifier.classify_async(chat_msgs, strategy=strategy_val)
    
    comp = result.score
    
    # Use category scores and tags from classifier
    category_scores = result.category_scores or {
        "Reasoning": 0.5, "Coding": 0.0, "Summary": 0.0, "Creative": 0.0
    }
    tags = result.tags or []

    # Dynamic weights derived directly from prompt category requirements
    weights = {
        "Reasoning": max(0.2, category_scores.get("Reasoning", 0.2) * 1.5),
        "Coding": category_scores.get("Coding", 0.0) * 2.5,
        "Summary": category_scores.get("Summary", 0.0) * 2.5,
        "Creative": category_scores.get("Creative", 0.0) * 2.5,
    }
    
    # Target baseline score depending on complexity
    target_score = 0.65 + (comp * 0.25) # from 0.65 to 0.90 based on complexity
    
    # Get available models
    models_resp = await list_models()
    all_models = models_resp.data
    
    # Filter by provider
    if request.providers:
        all_models = [m for m in all_models if m.provider and m.provider.lower() in [p.lower() for p in request.providers]]
    
    # Filter by budget: Free/Budget/Value/Pro/Any
    if request.budget and request.budget.lower() != "any":
        budget = request.budget.lower()
        if budget == "free":
            all_models = [m for m in all_models if (m.price_in or 0) == 0]
        elif budget == "budget":
            all_models = [m for m in all_models if (m.price_in or 0) <= 0.5]
        elif budget == "value":
            all_models = [m for m in all_models if (m.price_in or 0) <= 2.0]
        elif budget == "pro":
            all_models = [m for m in all_models if (m.price_in or 0) > 2.0]
            
    # Calculate fit for each model
    recommendations = []
    for m in all_models:
        scores = MODEL_BENCHMARKS.get(m.id, {"Reasoning": 0.8, "Coding": 0.8, "Summary": 0.8, "Creative": 0.8})

        weighted_sum = sum(scores[k] * weights[k] for k in weights)
        total_weight = sum(weights.values())
        model_score = weighted_sum / total_weight

        import math
        # Quality gate: does this model meet the complexity threshold?
        quality_meets = model_score >= target_score

        # Cost factor: logarithmic penalty for expensive models
        price = max(m.price_in or 0.01, 0.01)
        cost_penalty = math.log10(1 + price) * 0.15  # mild penalty for cost

        # Tier alignment bonus: models matching the classified tier get a clear boost
        classified_tier = result.tier.value if hasattr(result.tier, "value") else str(result.tier)
        tier_bonus = 0.22 if (m.tier and m.tier == classified_tier) else 0.0

        # For LOW complexity prompts (score < 0.4), strongly prefer cheap models
        if comp < 0.4:
            # Ultra-cheap models (<= 0.15) get highest bonus, cheap (<= 0.50) good bonus, frontier heavy penalty
            if (m.price_in or 0) <= 0.15:
                cost_bonus = 0.35
            elif (m.price_in or 0) <= 0.5:
                cost_bonus = 0.20
            elif (m.price_in or 0) <= 2.0:
                cost_bonus = -0.10
            else:
                cost_bonus = -0.35  # heavy penalty for frontier on simple tasks
            conf = max(0.01, min(0.99, model_score * 0.45 + cost_bonus + tier_bonus - cost_penalty))
        elif comp < 0.65:
            # MEDIUM complexity: balanced approach
            if quality_meets:
                cost_bonus = max(0, 0.25 - price / 15.0)
            else:
                cost_bonus = -0.15
            conf = max(0.01, min(0.99, model_score * 0.65 + cost_bonus + tier_bonus - cost_penalty * 0.5))
        else:
            # HIGH complexity: quality is paramount, cost secondary
            if model_score < target_score:
                penalty = (target_score - model_score) * 2.5
            else:
                penalty = 0.0
            cost_bonus = max(0, 0.15 - price / 30.0) if quality_meets else 0
            conf = max(0.01, min(0.99, model_score - penalty + cost_bonus + tier_bonus))

        recommendations.append({
            "model_id": m.id,
            "provider": m.provider,
            "tier": m.tier,
            "confidence": round(conf, 4),
            "price_in": m.price_in,
            "price_out": m.price_out,
            "price_cache_read": m.price_cache_read,
            "context_length": m.context_length
        })

    recommendations.sort(key=lambda x: x["confidence"], reverse=True)
    
    top_model = recommendations[0]["model_id"] if recommendations else "None"
    top_conf = recommendations[0]["confidence"] if recommendations else 0
    
    result.category_scores = category_scores
    result.tags = tags
    result.recommendations = recommendations[:10] # Top 10
    result.suggested_model = top_model
    result.confidence = top_conf

    if result.decision_trace is not None:
        from app.models import ChatCompletionRequest
        dummy_req = ChatCompletionRequest(
            model=top_model,
            messages=[ChatMessage(**m) for m in request.messages],
            strategy=strategy_val,
        )
        decision = router_engine.decide_route(dummy_req, strategy_override=strategy_val)
        fallback_candidates = [c.model_name for c in router_engine.get_fallback_candidates(decision)[:3]]
        result.decision_trace.update({
            "recommended_model": top_model,
            "recommended_confidence": top_conf,
            "applied_weights": {k: round(v, 2) for k, v in weights.items()},
            "planned_fallback_chain": [top_model] + fallback_candidates,
            "total_candidates_evaluated": len(all_models),
        })
    
    CLASSIFY_CACHE[cache_key] = result
    
    # Keep cache small to avoid memory leaks
    if len(CLASSIFY_CACHE) > 1000:
        CLASSIFY_CACHE.clear()
        
    return result


@app.post("/v1/classify/explain", response_model=ClassificationResult)
async def explain_classification(request: ClassifyRequest):
    """
    Detailed explainability endpoint: returns the complete decision trace,
    including individual heuristic signal deltas, category weights, and fallback chain.
    """
    return await classify_prompt(request)


@app.get("/v1/metrics/summary")
async def get_metrics_summary():
    """Retrieve aggregate usage and cost savings statistics."""
    return router_engine.metrics.get_summary()


@app.get("/v1/metrics/recent")
async def get_recent_metrics(limit: int = 50):
    """Retrieve recent routed completions log."""
    return router_engine.metrics.get_recent_requests(limit=limit)


@app.get("/v1/metrics/export/csv")
async def export_metrics_csv():
    """Export all metrics as a CSV file."""
    csv_data = router_engine.metrics.get_all_requests_csv()
    return Response(content=csv_data, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=llm_router_metrics.csv"
    })


@app.get("/v1/metrics/export/json")
async def export_metrics_json():
    """Export all metrics as a JSON file."""
    json_data = router_engine.metrics.get_all_requests_json()
    return Response(content=json_data, media_type="application/json", headers={
        "Content-Disposition": "attachment; filename=llm_router_metrics.json"
    })



@app.get("/v1/analytics")
async def get_analytics():
    """Rich analytics: model distribution, tier stats, time-series, efficiency."""
    return router_engine.metrics.get_analytics()


@app.delete("/v1/analytics")
async def clear_analytics():
    """Clear all request metrics and analytics from the database."""
    router_engine.metrics.clear_all()
    return {"status": "ok", "message": "All analytics cleared"}


@app.get("/v1/catalog/summary")
async def get_catalog_summary():
    """Quick overview of the curated model catalog."""
    providers = {}
    tiers = {"cheap": 0, "medium": 0, "frontier": 0}
    price_range = {"min_in": float("inf"), "max_in": 0, "min_out": float("inf"), "max_out": 0}

    for m in _curated_models:
        p = m.provider or "unknown"
        if p not in providers:
            providers[p] = {"count": 0, "models": []}
        providers[p]["count"] += 1
        providers[p]["models"].append(m.id)

        tier = m.tier or "cheap"
        tiers[tier] = tiers.get(tier, 0) + 1

        pin = m.price_in or 0
        pout = m.price_out or 0
        if pin < price_range["min_in"]: price_range["min_in"] = pin
        if pin > price_range["max_in"]: price_range["max_in"] = pin
        if pout < price_range["min_out"]: price_range["min_out"] = pout
        if pout > price_range["max_out"]: price_range["max_out"] = pout

    if price_range["min_in"] == float("inf"):
        price_range["min_in"] = 0.0
    if price_range["min_out"] == float("inf"):
        price_range["min_out"] = 0.0

    caching_models = [m for m in _curated_models if m.price_cache_read is not None]
    cache_discounts = [
        round((1.0 - (m.price_cache_read / m.price_in)) * 100, 1)
        for m in caching_models if m.price_in and m.price_in > 0
    ]
    prompt_caching_summary = {
        "supported_models": len(caching_models),
        "max_discount_pct": max(cache_discounts) if cache_discounts else 0.0,
        "avg_discount_pct": round(sum(cache_discounts) / len(cache_discounts), 1) if cache_discounts else 0.0,
    }

    return {
        "total_models": len(_curated_models),
        "providers": providers,
        "tier_distribution": tiers,
        "price_range_per_m": price_range,
        "prompt_caching": prompt_caching_summary,
        "last_updated": "2026-09-29",
    }


class EstimateCostRequest(BaseModel):
    messages: List[dict]
    estimated_completion_tokens: Optional[int] = 500
    cache_hit_rate: Optional[float] = 0.0
    tier: Optional[str] = None
    provider: Optional[str] = None


@app.post("/v1/estimate-cost", tags=["Cost"])
async def estimate_cost_endpoint(request: EstimateCostRequest):
    """
    Pre-execution cost estimator: estimate token count and cost across all curated models.
    Returns sorted results (cheapest first) with caching projections and context-fit checks.
    """
    from app.tokenizer import estimate_messages_tokens, estimate_cost_all_models

    prompt_tokens = estimate_messages_tokens(request.messages)

    estimates = estimate_cost_all_models(
        prompt_tokens=prompt_tokens,
        estimated_completion_tokens=request.estimated_completion_tokens or 500,
        cache_hit_rate=request.cache_hit_rate or 0.0,
        tier_filter=request.tier,
        provider_filter=request.provider,
    )

    # Calculate savings summary
    if len(estimates) >= 2:
        cheapest = estimates[0]["cost_total_usd"]
        most_expensive = estimates[-1]["cost_total_usd"]
        savings_potential = round(most_expensive - cheapest, 6) if most_expensive > 0 else 0.0
        savings_pct = round((1 - cheapest / most_expensive) * 100, 1) if most_expensive > 0 else 0.0
    else:
        savings_potential = 0.0
        savings_pct = 0.0

    return {
        "prompt_tokens_estimated": prompt_tokens,
        "completion_tokens_estimated": request.estimated_completion_tokens or 500,
        "cache_hit_rate": request.cache_hit_rate or 0.0,
        "estimates": estimates,
        "summary": {
            "cheapest_model": estimates[0]["model_id"] if estimates else None,
            "cheapest_cost_usd": estimates[0]["cost_total_usd"] if estimates else 0.0,
            "most_expensive_model": estimates[-1]["model_id"] if estimates else None,
            "most_expensive_cost_usd": estimates[-1]["cost_total_usd"] if estimates else 0.0,
            "savings_potential_usd": savings_potential,
            "savings_percentage": savings_pct,
            "total_models_evaluated": len(estimates),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
