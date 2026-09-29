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



@app.post("/v1/classify", response_model=ClassificationResult)
async def classify_prompt(request: ClassifyRequest):
    """
    Classify a conversation to suggest an optimal model tier and return UI metadata.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")
    
    # Run classifier
    chat_req = [m for m in request.messages] # just pass dicts or whatever format router_engine expects, it usually takes ChatMessage, but let's pass to classifier.
    # Actually classifier.classify_async expects List[ChatMessage]
    from app.models import ChatMessage
    chat_msgs = [ChatMessage(**m) for m in request.messages]
    
    result = await router_engine.classifier.classify_async(chat_msgs)
    
    # Generate scores based on complexity
    comp = result.score
    category_scores = {
        "Reasoning": min(1.0, comp * 1.2),
        "Coding": min(1.0, comp * 0.9 if "def " not in str(request.messages) else comp * 1.5),
        "Summary": min(1.0, comp * 0.8),
        "Creative": min(1.0, (1 - comp) * 1.2)
    }
    
    tags = []
    if category_scores["Reasoning"] > 0.6: tags.append("Reasoning")
    if category_scores["Coding"] > 0.6: tags.append("Coding")
    if sum(len(m.get("content", "")) for m in request.messages) > 1000: tags.append("Long")
    
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
            
    # Sort models by how well they match complexity vs cost
    recommendations = []
    for m in all_models:
        # Fake logic: closer price to complexity = better
        target_price = comp * 5.0
        actual_price = m.price_in or 0.1
        diff = abs(target_price - actual_price)
        conf = max(0.01, 1.0 - (diff / 10.0))
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
