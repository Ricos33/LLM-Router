from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

from app.backends.agy import DEFAULT_AGY_TIER_MAP


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Classifier
    classifier_mode: str = "mock"  # 'mock' or 'jev'
    classifier_confidence_threshold: float = 0.70
    jev_api_key: str = ""
    jev_api_base_url: str = "https://api.typesafe.ai/v1"

    # Cheap Backend (e.g. Local Ollama)
    cheap_provider: str = "ollama"  # 'ollama' or 'openai_compatible'
    cheap_api_base_url: str = "http://localhost:11434/v1"
    cheap_api_key: str = "ollama"
    cheap_model: str = "llama3.2:3b"
    cheap_prompt_price_per_m: float = 0.15      # $ / 1M prompt tokens (0 for pure local)
    cheap_completion_price_per_m: float = 0.60  # $ / 1M completion tokens

    # Frontier Backend (OpenAI / OpenRouter / Anthropic)
    frontier_provider: str = "openai_compatible"
    frontier_api_base_url: str = "https://api.openai.com/v1"
    frontier_api_key: str = ""
    frontier_model: str = "gpt-4o"
    frontier_prompt_price_per_m: float = 5.00      # $ / 1M prompt tokens
    frontier_completion_price_per_m: float = 15.00  # $ / 1M completion tokens

    # Agy Backend (Local Antigravity CLI)
    agy_enabled: bool = False
    agy_binary_path: str = "~/workspace/cli-tools/bin/agy"
    agy_timeout: float = 60.0
    agy_tier_map: Dict[str, Any] = Field(default_factory=lambda: DEFAULT_AGY_TIER_MAP.copy())
    agy_prompt_price_per_m: float = 0.0      # Subscription / local CLI
    agy_completion_price_per_m: float = 0.0

    # Medium Tier Pricing (if routed to non-agy medium backend)
    medium_prompt_price_per_m: float = 1.00
    medium_completion_price_per_m: float = 3.00

    # Routing & Fallbacks
    simulate_fallback: bool = True  # Fallback to simulated response if remote upstream is offline
    default_routing_tier: str = "auto"  # 'auto', 'cheap', 'medium', 'frontier'

    # Database
    database_url: str = "sqlite:///./data/metrics.sqlite3"
    db_path: Path = Path("./data/metrics.sqlite3")

    @field_validator("agy_tier_map", mode="before")
    @classmethod
    def parse_agy_tier_map(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            import json
            try:
                v = json.loads(v)
            except Exception:
                return DEFAULT_AGY_TIER_MAP.copy()
        if not isinstance(v, dict):
            return DEFAULT_AGY_TIER_MAP.copy()

        normalized = {}
        for tier, config in v.items():
            if isinstance(config, str):
                normalized[tier] = {"model": config, "effort": None}
            elif isinstance(config, dict):
                normalized[tier] = config
            else:
                normalized[tier] = {"model": str(config), "effort": None}
        return normalized


settings = Settings()
