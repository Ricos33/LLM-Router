from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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

    # Routing & Fallbacks
    simulate_fallback: bool = True  # Fallback to simulated response if remote upstream is offline
    default_routing_tier: str = "auto"  # 'auto', 'cheap', 'frontier'

    # Database
    database_url: str = "sqlite:///./data/metrics.sqlite3"
    db_path: Path = Path("./data/metrics.sqlite3")


settings = Settings()
