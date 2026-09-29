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
    # Anthropic
    ModelObject(id="anthropic/claude-3-5-sonnet-20240620", name="Claude 3.5 Sonnet", provider="anthropic", tier="frontier", price_in=3.0, price_out=15.0, context_length=200000),
    ModelObject(id="anthropic/claude-3-haiku-20240307", name="Claude 3 Haiku", provider="anthropic", tier="cheap", price_in=0.25, price_out=1.25, context_length=200000),
    ModelObject(id="anthropic/claude-3-opus-20240229", name="Claude 3 Opus", provider="anthropic", tier="frontier", price_in=15.0, price_out=75.0, context_length=200000),
    
    # OpenAI
    ModelObject(id="openai/gpt-4o", name="GPT-4o", provider="openai", tier="frontier", price_in=5.0, price_out=15.0, context_length=128000),
    ModelObject(id="openai/gpt-4o-mini", name="GPT-4o Mini", provider="openai", tier="cheap", price_in=0.15, price_out=0.6, context_length=128000),
    ModelObject(id="openai/o1-preview", name="o1-preview", provider="openai", tier="frontier", price_in=15.0, price_out=60.0, context_length=128000),
    ModelObject(id="openai/o1-mini", name="o1-mini", provider="openai", tier="medium", price_in=3.0, price_out=12.0, context_length=128000),
    
    # Google
    ModelObject(id="google/gemini-1.5-pro", name="Gemini 1.5 Pro", provider="google", tier="frontier", price_in=3.5, price_out=10.5, context_length=2000000),
    ModelObject(id="google/gemini-1.5-flash", name="Gemini 1.5 Flash", provider="google", tier="cheap", price_in=0.075, price_out=0.3, context_length=1000000),
    
    # Qwen (Alibaba)
    ModelObject(id="qwen/qwen-2.5-72b-instruct", name="Qwen 2.5 72B", provider="qwen", tier="medium", price_in=0.4, price_out=0.4, context_length=128000),
    ModelObject(id="qwen/qwen-2.5-7b-instruct", name="Qwen 2.5 7B", provider="qwen", tier="cheap", price_in=0.1, price_out=0.1, context_length=128000),
    
    # Mistral
    ModelObject(id="mistral/mistral-large-2407", name="Mistral Large 2", provider="mistral", tier="frontier", price_in=2.0, price_out=6.0, context_length=128000),
    ModelObject(id="mistral/mistral-nemo", name="Mistral Nemo", provider="mistral", tier="cheap", price_in=0.15, price_out=0.15, context_length=128000),
    
    # DeepSeek
    ModelObject(id="deepseek/deepseek-coder-v2", name="DeepSeek Coder V2", provider="deepseek", tier="medium", price_in=0.14, price_out=0.28, context_length=128000),
    ModelObject(id="deepseek/deepseek-chat-v2.5", name="DeepSeek V2.5", provider="deepseek", tier="medium", price_in=0.14, price_out=0.28, context_length=128000),
    
    # Meta (Llama)
    ModelObject(id="meta/llama-3.1-405b-instruct", name="Llama 3.1 405B", provider="meta", tier="frontier", price_in=2.7, price_out=2.7, context_length=128000),
    ModelObject(id="meta/llama-3.1-70b-instruct", name="Llama 3.1 70B", provider="meta", tier="medium", price_in=0.4, price_out=0.4, context_length=128000),
    ModelObject(id="meta/llama-3.1-8b-instruct", name="Llama 3.1 8B", provider="meta", tier="cheap", price_in=0.05, price_out=0.05, context_length=128000),
    
    # xAI (Grok)
    ModelObject(id="xai/grok-2", name="Grok 2", provider="xai", tier="frontier", price_in=2.0, price_out=4.0, context_length=128000),
    ModelObject(id="xai/grok-2-mini", name="Grok 2 Mini", provider="xai", tier="medium", price_in=0.2, price_out=0.4, context_length=128000),
]

@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    return ModelListResponse(data=_curated_models)
@app.get("/v1/models/tiers")
async def get_tier_models():
    """Retrieve configured tier-to-model mapping and metadata."""
    return router_engine.get_tier_models()


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    response: Response,
    x_router_tier: Optional[str] = Header(None, alias="X-Router-Tier"),
):
    """
    OpenAI-compatible chat completions endpoint.
    Dynamically routes queries based on prompt complexity or explicit overrides.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

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
    "anthropic/claude-3-5-sonnet-20240620": {"Reasoning": 0.92, "Coding": 0.93, "Summary": 0.90, "Creative": 0.88},
    "anthropic/claude-3-haiku-20240307": {"Reasoning": 0.75, "Coding": 0.70, "Summary": 0.82, "Creative": 0.78},
    "anthropic/claude-3-opus-20240229": {"Reasoning": 0.88, "Coding": 0.85, "Summary": 0.89, "Creative": 0.95},
    "openai/gpt-4o": {"Reasoning": 0.91, "Coding": 0.92, "Summary": 0.88, "Creative": 0.90},
    "openai/gpt-4o-mini": {"Reasoning": 0.82, "Coding": 0.81, "Summary": 0.85, "Creative": 0.80},
    "openai/o1-preview": {"Reasoning": 0.98, "Coding": 0.95, "Summary": 0.85, "Creative": 0.75},
    "openai/o1-mini": {"Reasoning": 0.95, "Coding": 0.96, "Summary": 0.75, "Creative": 0.65},
    "google/gemini-1.5-pro": {"Reasoning": 0.90, "Coding": 0.89, "Summary": 0.94, "Creative": 0.91},
    "google/gemini-1.5-flash": {"Reasoning": 0.80, "Coding": 0.78, "Summary": 0.87, "Creative": 0.83},
    "qwen/qwen-2.5-72b-instruct": {"Reasoning": 0.87, "Coding": 0.86, "Summary": 0.85, "Creative": 0.84},
    "qwen/qwen-2.5-7b-instruct": {"Reasoning": 0.74, "Coding": 0.73, "Summary": 0.75, "Creative": 0.72},
    "mistral/mistral-large-2407": {"Reasoning": 0.88, "Coding": 0.85, "Summary": 0.86, "Creative": 0.85},
    "mistral/mistral-nemo": {"Reasoning": 0.76, "Coding": 0.72, "Summary": 0.77, "Creative": 0.75},
    "deepseek/deepseek-coder-v2": {"Reasoning": 0.86, "Coding": 0.94, "Summary": 0.80, "Creative": 0.75},
    "deepseek/deepseek-chat-v2.5": {"Reasoning": 0.88, "Coding": 0.89, "Summary": 0.84, "Creative": 0.82},
    "meta/llama-3.1-405b-instruct": {"Reasoning": 0.89, "Coding": 0.88, "Summary": 0.86, "Creative": 0.87},
    "meta/llama-3.1-70b-instruct": {"Reasoning": 0.85, "Coding": 0.84, "Summary": 0.83, "Creative": 0.82},
    "meta/llama-3.1-8b-instruct": {"Reasoning": 0.70, "Coding": 0.65, "Summary": 0.72, "Creative": 0.70},
    "xai/grok-2": {"Reasoning": 0.89, "Coding": 0.88, "Summary": 0.85, "Creative": 0.92},
    "xai/grok-2-mini": {"Reasoning": 0.81, "Coding": 0.79, "Summary": 0.80, "Creative": 0.84},
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
        
        # Penalize models that don't meet the target_score (complexity requirement)
        if model_score < target_score:
            penalty = (target_score - model_score) * 2.0 # Heavy penalty for being too dumb
        else:
            penalty = 0.0
            
        # Reward cheaper models IF they meet the target score
        price_factor = (m.price_in or 0.1) / 10.0 # Normalized roughly 0 to 1.5
        cost_efficiency = 0.0
        if model_score >= target_score:
            cost_efficiency = max(0, 0.5 - price_factor) # Bonus for being cheap but smart enough
            
        conf = max(0.01, min(0.99, model_score - penalty + cost_efficiency))
        
        recommendations.append({
            "model_id": m.id,
            "provider": m.provider,
            "confidence": conf,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
