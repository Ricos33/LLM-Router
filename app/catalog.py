from typing import Optional, Dict, Any, List
from app.models import ModelObject

CURATED_MODELS: List[ModelObject] = [
    # ── Anthropic (Claude) ── latest Sept 2026 (90% prompt cache discount)
    ModelObject(id="anthropic/claude-opus-5.5", name="Claude Opus 5.5", provider="anthropic", tier="frontier", price_in=4.0, price_out=20.0, price_cache_read=0.40, context_length=200000),
    ModelObject(id="anthropic/claude-fable-5.1", name="Claude Fable 5.1", provider="anthropic", tier="frontier", price_in=10.0, price_out=50.0, price_cache_read=1.00, context_length=200000),
    ModelObject(id="anthropic/claude-sonnet-5", name="Claude Sonnet 5", provider="anthropic", tier="medium", price_in=2.0, price_out=10.0, price_cache_read=0.20, context_length=200000),
    ModelObject(id="anthropic/claude-haiku-4.5", name="Claude Haiku 4.5", provider="anthropic", tier="cheap", price_in=1.0, price_out=5.0, price_cache_read=0.10, context_length=200000),

    # ── OpenAI (GPT) ── latest Sept 2026 (50% prompt cache discount)
    ModelObject(id="openai/gpt-6-astra", name="GPT-6 Astra", provider="openai", tier="frontier", price_in=10.0, price_out=50.0, price_cache_read=5.00, context_length=256000),
    ModelObject(id="openai/gpt-5.6-sol", name="GPT-5.6 Sol", provider="openai", tier="frontier", price_in=4.0, price_out=20.0, price_cache_read=2.00, context_length=200000),
    ModelObject(id="openai/gpt-5.6-terra", name="GPT-5.6 Terra", provider="openai", tier="medium", price_in=2.0, price_out=12.0, price_cache_read=1.00, context_length=200000),
    ModelObject(id="openai/gpt-5.6-luna", name="GPT-5.6 Luna", provider="openai", tier="cheap", price_in=0.20, price_out=1.20, price_cache_read=0.10, context_length=128000),

    # ── Google (Gemini) ── latest Sept 2026 (75% context caching discount)
    ModelObject(id="google/gemini-3.1-pro", name="Gemini 3.1 Pro", provider="google", tier="frontier", price_in=2.0, price_out=12.0, price_cache_read=0.50, context_length=2000000),
    ModelObject(id="google/gemini-3.8-flash", name="Gemini 3.8 Flash", provider="google", tier="medium", price_in=0.75, price_out=3.75, price_cache_read=0.1875, context_length=1000000),
    ModelObject(id="google/gemini-3.5-flash-lite", name="Gemini 3.5 Flash-Lite", provider="google", tier="cheap", price_in=0.30, price_out=2.50, price_cache_read=0.075, context_length=1000000),

    # ── Qwen (Alibaba) ── latest Sept 2026 (80% prompt cache discount)
    ModelObject(id="qwen/qwen3.8-max", name="Qwen 3.8 Max", provider="qwen", tier="frontier", price_in=2.0, price_out=6.0, price_cache_read=0.40, context_length=128000),
    ModelObject(id="qwen/qwen3.8-max-prime", name="Qwen 3.8 Max Prime", provider="qwen", tier="frontier", price_in=4.0, price_out=12.0, price_cache_read=0.80, context_length=128000),
    ModelObject(id="qwen/qwen3.8-27b", name="Qwen 3.8 27B", provider="qwen", tier="cheap", price_in=0.10, price_out=0.50, price_cache_read=0.02, context_length=128000),

    # ── Mistral ── latest Sept 2026 (50% prefix cache discount)
    ModelObject(id="mistral/mistral-large-3", name="Mistral Large 3", provider="mistral", tier="medium", price_in=0.50, price_out=1.50, price_cache_read=0.25, context_length=128000),
    ModelObject(id="mistral/mistral-small-4", name="Mistral Small 4", provider="mistral", tier="cheap", price_in=0.15, price_out=0.60, price_cache_read=0.075, context_length=128000),

    # ── DeepSeek ── latest Sept 2026 (90% prompt cache discount)
    ModelObject(id="deepseek/deepseek-v4-pro", name="DeepSeek V4 Pro", provider="deepseek", tier="medium", price_in=1.32, price_out=3.96, price_cache_read=0.132, context_length=128000),
    ModelObject(id="deepseek/deepseek-v4.1-flash", name="DeepSeek V4.1 Flash", provider="deepseek", tier="cheap", price_in=0.30, price_out=1.20, price_cache_read=0.03, context_length=128000),

    # ── Meta (Llama / Muse) ── latest Sept 2026 (80% prompt cache discount)
    ModelObject(id="meta/muse-spark-1.3", name="Muse Spark 1.3", provider="meta", tier="frontier", price_in=1.25, price_out=4.25, price_cache_read=0.25, context_length=256000),
    ModelObject(id="meta/llama-4-scout", name="Llama 4 Scout", provider="meta", tier="cheap", price_in=0.05, price_out=0.30, price_cache_read=0.01, context_length=128000),
    ModelObject(id="meta/llama-4-maverick", name="Llama 4 Maverick", provider="meta", tier="medium", price_in=0.20, price_out=0.80, price_cache_read=0.04, context_length=128000),

    # ── xAI (Grok) ── latest Sept 2026 (75% prompt cache discount)
    ModelObject(id="xai/grok-4.7", name="Grok 4.7", provider="xai", tier="frontier", price_in=2.0, price_out=6.0, price_cache_read=0.50, context_length=200000),
    ModelObject(id="xai/grok-4.7-fast", name="Grok 4.7 Fast", provider="xai", tier="medium", price_in=1.0, price_out=3.0, price_cache_read=0.25, context_length=200000),
]

MODEL_BENCHMARKS: Dict[str, Dict[str, float]] = {
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

_MODEL_MAP: Dict[str, ModelObject] = {m.id.lower(): m for m in CURATED_MODELS}

def get_model_by_id(model_id: str) -> Optional[ModelObject]:
    """Lookup a model by ID or normalized name."""
    if not model_id:
        return None
    clean = model_id.strip().lower()
    if clean in _MODEL_MAP:
        return _MODEL_MAP[clean]
    # Check partial match (e.g. "claude-opus-5.5" matches "anthropic/claude-opus-5.5")
    for mid, m in _MODEL_MAP.items():
        if mid.endswith(f"/{clean}") or mid == clean:
            return m
    return None

def get_model_pricing(model_id: str) -> tuple[float, float]:
    """Return (price_in, price_out) in $/1M tokens for a given model."""
    m = get_model_by_id(model_id)
    if m:
        return (m.price_in or 0.0, m.price_out or 0.0)
    return (0.0, 0.0)

def get_model_cache_pricing(model_id: str) -> Optional[float]:
    """Return price_cache_read in $/1M tokens for a given model if supported."""
    m = get_model_by_id(model_id)
    if m and m.price_cache_read is not None:
        return m.price_cache_read
    return None
