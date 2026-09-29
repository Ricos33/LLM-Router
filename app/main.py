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

from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelListResponse,
    ModelObject,
)
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



_curated_models = [
    # ── Anthropic (Claude) ── latest Sept 2026
    ModelObject(id="anthropic/claude-opus-5.5", name="Claude Opus 5.5", provider="anthropic", tier="frontier", price_in=4.0, price_out=20.0, context_length=200000),
    ModelObject(id="anthropic/claude-fable-5.1", name="Claude Fable 5.1", provider="anthropic", tier="frontier", price_in=10.0, price_out=50.0, context_length=200000),
    ModelObject(id="anthropic/claude-sonnet-5", name="Claude Sonnet 5", provider="anthropic", tier="medium", price_in=2.0, price_out=10.0, context_length=200000),
    ModelObject(id="anthropic/claude-haiku-4.5", name="Claude Haiku 4.5", provider="anthropic", tier="cheap", price_in=1.0, price_out=5.0, context_length=200000),

    # ── OpenAI (GPT) ── latest Sept 2026
    ModelObject(id="openai/gpt-6-astra", name="GPT-6 Astra", provider="openai", tier="frontier", price_in=10.0, price_out=50.0, context_length=256000),
    ModelObject(id="openai/gpt-5.6-sol", name="GPT-5.6 Sol", provider="openai", tier="frontier", price_in=4.0, price_out=20.0, context_length=200000),
    ModelObject(id="openai/gpt-5.6-terra", name="GPT-5.6 Terra", provider="openai", tier="medium", price_in=2.0, price_out=12.0, context_length=200000),
    ModelObject(id="openai/gpt-5.6-luna", name="GPT-5.6 Luna", provider="openai", tier="cheap", price_in=0.20, price_out=1.20, context_length=128000),

    # ── Google (Gemini) ── latest Sept 2026
    ModelObject(id="google/gemini-3.1-pro", name="Gemini 3.1 Pro", provider="google", tier="frontier", price_in=2.0, price_out=12.0, context_length=2000000),
    ModelObject(id="google/gemini-3.8-flash", name="Gemini 3.8 Flash", provider="google", tier="medium", price_in=0.75, price_out=3.75, context_length=1000000),
    ModelObject(id="google/gemini-3.5-flash-lite", name="Gemini 3.5 Flash-Lite", provider="google", tier="cheap", price_in=0.30, price_out=2.50, context_length=1000000),

    # ── Qwen (Alibaba) ── latest Sept 2026
    ModelObject(id="qwen/qwen3.8-max", name="Qwen 3.8 Max", provider="qwen", tier="frontier", price_in=2.0, price_out=6.0, context_length=128000),
    ModelObject(id="qwen/qwen3.8-max-prime", name="Qwen 3.8 Max Prime", provider="qwen", tier="frontier", price_in=4.0, price_out=12.0, context_length=128000),
    ModelObject(id="qwen/qwen3.8-27b", name="Qwen 3.8 27B", provider="qwen", tier="cheap", price_in=0.10, price_out=0.50, context_length=128000),

    # ── Mistral ── latest Sept 2026
    ModelObject(id="mistral/mistral-large-3", name="Mistral Large 3", provider="mistral", tier="medium", price_in=0.50, price_out=1.50, context_length=128000),
    ModelObject(id="mistral/mistral-small-4", name="Mistral Small 4", provider="mistral", tier="cheap", price_in=0.15, price_out=0.60, context_length=128000),

    # ── DeepSeek ── latest Sept 2026
    ModelObject(id="deepseek/deepseek-v4-pro", name="DeepSeek V4 Pro", provider="deepseek", tier="medium", price_in=1.32, price_out=3.96, context_length=128000),
    ModelObject(id="deepseek/deepseek-v4.1-flash", name="DeepSeek V4.1 Flash", provider="deepseek", tier="cheap", price_in=0.30, price_out=1.20, context_length=128000),

    # ── Meta (Llama / Muse) ── latest Sept 2026
    ModelObject(id="meta/muse-spark-1.3", name="Muse Spark 1.3", provider="meta", tier="frontier", price_in=1.25, price_out=4.25, context_length=256000),
    ModelObject(id="meta/llama-4-scout", name="Llama 4 Scout", provider="meta", tier="cheap", price_in=0.05, price_out=0.30, context_length=128000),
    ModelObject(id="meta/llama-4-maverick", name="Llama 4 Maverick", provider="meta", tier="medium", price_in=0.20, price_out=0.80, context_length=128000),

    # ── xAI (Grok) ── latest Sept 2026
    ModelObject(id="xai/grok-4.7", name="Grok 4.7", provider="xai", tier="frontier", price_in=2.0, price_out=6.0, context_length=200000),
    ModelObject(id="xai/grok-4.7-fast", name="Grok 4.7 Fast", provider="xai", tier="medium", price_in=1.0, price_out=3.0, context_length=200000),
]

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


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    response: Response,
    x_router_tier: Optional[str] = Header(None, alias="X-Router-Tier"),
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
            request, tier_header_override=x_router_tier
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
            
            for k, v in headers_dict.items():
                response.headers[k] = v

        if request.stream:
            async def stream_generator():
                content = completion.choices[0].message.content
                chunk_size = 4
                response_id = completion.id
                model = completion.model
                
                # Initial role chunk
                yield f"data: {json.dumps({'id': response_id, 'object': 'chat.completion.chunk', 'model': model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\\n\\n"
                
                # Content chunks
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    yield f"data: {json.dumps({'id': response_id, 'object': 'chat.completion.chunk', 'model': model, 'choices': [{'index': 0, 'delta': {'content': chunk}, 'finish_reason': None}]})}\\n\\n"
                    await asyncio.sleep(0.01) # Simulate network delay
                
                # Final chunk
                yield f"data: {json.dumps({'id': response_id, 'object': 'chat.completion.chunk', 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\\n\\n"
                yield "data: [DONE]\\n\\n"
            
            return StreamingResponse(stream_generator(), media_type="text/event-stream", headers=headers_dict)

        return completion

    except Exception as e:
        logger.error(f"Routing completion failure: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM Router gateway error: {str(e)}")



MODEL_BENCHMARKS = {
    # ── Anthropic ──
    "anthropic/claude-opus-5.5":    {"Reasoning": 0.97, "Coding": 0.96, "Summary": 0.93, "Creative": 0.94},
    "anthropic/claude-fable-5.1":   {"Reasoning": 0.95, "Coding": 0.91, "Summary": 0.96, "Creative": 0.97},
    "anthropic/claude-sonnet-5":    {"Reasoning": 0.90, "Coding": 0.92, "Summary": 0.89, "Creative": 0.88},
    "anthropic/claude-haiku-4.5":   {"Reasoning": 0.81, "Coding": 0.79, "Summary": 0.84, "Creative": 0.82},
    # ── OpenAI ──
    "openai/gpt-6-astra":          {"Reasoning": 0.96, "Coding": 0.95, "Summary": 0.91, "Creative": 0.93},
    "openai/gpt-5.6-sol":          {"Reasoning": 0.92, "Coding": 0.93, "Summary": 0.88, "Creative": 0.89},
    "openai/gpt-5.6-terra":        {"Reasoning": 0.87, "Coding": 0.88, "Summary": 0.86, "Creative": 0.85},
    "openai/gpt-5.6-luna":         {"Reasoning": 0.78, "Coding": 0.76, "Summary": 0.82, "Creative": 0.80},
    # ── Google ──
    "google/gemini-3.1-pro":       {"Reasoning": 0.93, "Coding": 0.91, "Summary": 0.95, "Creative": 0.90},
    "google/gemini-3.8-flash":     {"Reasoning": 0.86, "Coding": 0.85, "Summary": 0.90, "Creative": 0.87},
    "google/gemini-3.5-flash-lite": {"Reasoning": 0.77, "Coding": 0.74, "Summary": 0.83, "Creative": 0.79},
    # ── Qwen ──
    "qwen/qwen3.8-max":            {"Reasoning": 0.91, "Coding": 0.92, "Summary": 0.87, "Creative": 0.86},
    "qwen/qwen3.8-max-prime":      {"Reasoning": 0.93, "Coding": 0.94, "Summary": 0.89, "Creative": 0.88},
    "qwen/qwen3.8-27b":            {"Reasoning": 0.76, "Coding": 0.78, "Summary": 0.75, "Creative": 0.73},
    # ── Mistral ──
    "mistral/mistral-large-3":     {"Reasoning": 0.88, "Coding": 0.87, "Summary": 0.86, "Creative": 0.85},
    "mistral/mistral-small-4":     {"Reasoning": 0.79, "Coding": 0.77, "Summary": 0.80, "Creative": 0.78},
    # ── DeepSeek ──
    "deepseek/deepseek-v4-pro":    {"Reasoning": 0.90, "Coding": 0.93, "Summary": 0.85, "Creative": 0.83},
    "deepseek/deepseek-v4.1-flash": {"Reasoning": 0.82, "Coding": 0.86, "Summary": 0.80, "Creative": 0.77},
    # ── Meta ──
    "meta/muse-spark-1.3":         {"Reasoning": 0.92, "Coding": 0.90, "Summary": 0.91, "Creative": 0.93},
    "meta/llama-4-scout":          {"Reasoning": 0.73, "Coding": 0.71, "Summary": 0.74, "Creative": 0.72},
    "meta/llama-4-maverick":       {"Reasoning": 0.84, "Coding": 0.83, "Summary": 0.82, "Creative": 0.81},
    # ── xAI ──
    "xai/grok-4.7":                {"Reasoning": 0.94, "Coding": 0.92, "Summary": 0.88, "Creative": 0.95},
    "xai/grok-4.7-fast":           {"Reasoning": 0.87, "Coding": 0.85, "Summary": 0.83, "Creative": 0.88},
}

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
    cache_key = hashlib.md5(f"{full_text}_{request.budget}_{','.join(request.providers or [])}".encode()).hexdigest()
    
    if cache_key in CLASSIFY_CACHE:
        return CLASSIFY_CACHE[cache_key]
    
    # Run classifier
    from app.models import ChatMessage
    chat_msgs = [ChatMessage(**m) for m in request.messages]
    
    result = await router_engine.classifier.classify_async(chat_msgs)
    
    comp = result.score
    
    # Simple heuristic to determine prompt weights
    full_text = " ".join([m.get("content", "") for m in request.messages]).lower()
    
    is_coding = any(k in full_text for k in ["def ", "class ", "function", "react", "html", "css", "bug", "error", "script"])
    is_summary = any(k in full_text for k in ["summarize", "tldr", "tl;dr", "resume", "shorten"])
    is_creative = any(k in full_text for k in ["poem", "story", "joke", "imagine", "write a", "blog"])
    
    tags = []
    if is_coding: tags.append("Coding")
    if is_summary: tags.append("Summary")
    if is_creative: tags.append("Creative")
    if comp > 0.7 or not (is_coding or is_summary or is_creative): 
        tags.append("Reasoning")
    if len(full_text) > 1000: tags.append("Long")

    # Weights for scoring
    weights = {"Reasoning": 1.0, "Coding": 0.0, "Summary": 0.0, "Creative": 0.0}
    if is_coding: weights["Coding"] = 2.0; weights["Reasoning"] = 0.5
    if is_summary: weights["Summary"] = 2.0; weights["Reasoning"] = 0.5
    if is_creative: weights["Creative"] = 2.0; weights["Reasoning"] = 0.5
    
    # Target baseline score depending on complexity
    target_score = 0.65 + (comp * 0.25) # from 0.65 to 0.90 based on complexity
    
    category_scores = {k: min(1.0, comp * (1.2 if k in tags else 0.8)) for k in ["Reasoning", "Coding", "Summary", "Creative"]}
    
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

        # For LOW complexity prompts (score < 0.4), strongly prefer cheap models
        if comp < 0.4:
            # Cheap models get a big bonus; frontier models get heavy cost penalty
            if (m.price_in or 0) <= 0.5:
                cost_bonus = 0.25  # strong bonus for being cheap
            elif (m.price_in or 0) <= 2.0:
                cost_bonus = 0.10
            else:
                cost_bonus = -0.20  # penalty for frontier on simple tasks
            conf = max(0.01, min(0.99, model_score * 0.6 + cost_bonus - cost_penalty))
        elif comp < 0.65:
            # MEDIUM complexity: balanced approach
            if quality_meets:
                cost_bonus = max(0, 0.3 - price / 15.0)
            else:
                cost_bonus = -0.15
            conf = max(0.01, min(0.99, model_score * 0.7 + cost_bonus - cost_penalty * 0.5))
        else:
            # HIGH complexity: quality is paramount, cost secondary
            if model_score < target_score:
                penalty = (target_score - model_score) * 2.5
            else:
                penalty = 0.0
            cost_bonus = max(0, 0.15 - price / 30.0) if quality_meets else 0
            conf = max(0.01, min(0.99, model_score - penalty + cost_bonus))

        recommendations.append({
            "model_id": m.id,
            "provider": m.provider,
            "confidence": round(conf, 4),
            "price_in": m.price_in,
            "price_out": m.price_out,
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
    
    CLASSIFY_CACHE[cache_key] = result
    
    # Keep cache small to avoid memory leaks
    if len(CLASSIFY_CACHE) > 1000:
        CLASSIFY_CACHE.clear()
        
    return result
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



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
