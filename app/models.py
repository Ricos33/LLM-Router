import time
import uuid
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str = "router-auto"
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    user: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class CompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class RouterMetadata(BaseModel):
    routed_tier: str
    classifier_score: float
    classifier_reasons: List[str]
    actual_model: str
    upstream_provider: str
    latency_ms: float
    cost_actual_usd: float
    cost_frontier_usd: float
    cost_saved_usd: float
    fallback_triggered: bool = False
    fallback_chain: List[str] = Field(default_factory=list)
    circuit_status: Optional[str] = "healthy"
    cost_cached_usd: Optional[float] = None
    cache_savings_pct: Optional[float] = None



class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: CompletionUsage
    router_metadata: Optional[RouterMetadata] = None


class ModelObject(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "llm-router"
    name: Optional[str] = None
    provider: Optional[str] = None
    tier: Optional[str] = None
    price_in: Optional[float] = None
    price_out: Optional[float] = None
    price_cache_read: Optional[float] = None
    context_length: Optional[int] = None
    scores: Optional[Dict[str, float]] = None


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelObject]


class ModelCompareResult(BaseModel):
    model: str
    provider: Optional[str] = "unknown"
    tier: Optional[str] = "medium"
    content: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    error: Optional[str] = None


class CompareRequest(BaseModel):
    messages: List[ChatMessage]
    models: Optional[List[str]] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    provider_keys: Optional[Dict[str, str]] = None


class CompareResponse(BaseModel):
    prompt: str
    results: List[ModelCompareResult]
    cheapest_model: Optional[str] = None
    fastest_model: Optional[str] = None
    cost_spread_usd: float = 0.0
