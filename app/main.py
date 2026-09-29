import logging
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
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


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    """List available virtual router models and upstream targets."""
    models = [
        ModelObject(id="router-auto"),
        ModelObject(id="router-cheap"),
        ModelObject(id="router-medium"),
        ModelObject(id="router-frontier"),
        ModelObject(id=settings.cheap_model),
        ModelObject(id=settings.frontier_model),
        ModelObject(id=settings.openai_model),
        ModelObject(id=settings.anthropic_model),
    ]
    if settings.agy_enabled:
        models.extend([
            ModelObject(id="agy-cheap"),
            ModelObject(id="agy-medium"),
            ModelObject(id="agy-frontier"),
        ])
    return ModelListResponse(data=models)


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

        # Inject diagnostic routing headers
        if completion.router_metadata:
            meta = completion.router_metadata
            response.headers["X-Router-Tier"] = meta.routed_tier
            response.headers["X-Router-Model"] = meta.actual_model
            response.headers["X-Router-Latency-MS"] = str(meta.latency_ms)
            response.headers["X-Router-Saved-USD"] = str(meta.cost_saved_usd)
            response.headers["X-Router-Score"] = str(meta.classifier_score)

        return completion

    except Exception as e:
        logger.error(f"Routing completion failure: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"LLM Router gateway error: {str(e)}")


@app.post("/v1/classify", response_model=ClassificationResult)
async def classify_prompt(request: ChatCompletionRequest):
    """
    Classify a conversation to suggest an optimal model tier without generating a completion.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")
    
    # Run classifier
    result = await router_engine.classifier.classify_async(request.messages)
    tier_models = router_engine.get_tier_models()
    result.tier_models = tier_models
    if result.tier.value in tier_models:
        result.suggested_model = tier_models[result.tier.value]["model"]
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
