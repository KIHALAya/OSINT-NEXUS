# core/config.py
from functools import lru_cache
from typing import Optional, Any
from pydantic import field_validator, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated

def empty_str_to_none(v: Any) -> Any:
    if v == "":
        return None
    return v

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database & Infrastructure
    DATABASE_URL: str = "postgresql+asyncpg://nexus:nexus@localhost:5432/nexus"
    QDRANT_URL: str = "http://localhost:6333"
    REDIS_URL: str = "redis://localhost:6379"
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = None
    APIFY_TOKEN: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    GOOGLE_VISION_API_KEY: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    # Local/Hosted LLM (Gemma 4)
    LLM_PROVIDER: str = "ollama"  # "ollama", "groq", "google", or "openrouter"
    LLM_API_KEY: Optional[str] = None
    LOCAL_LLM_URL: str = "http://localhost:11434/v1"
    LOCAL_LLM_MODEL: str = "gemma4" 
    
    # Hosted Gemma Models
    GROQ_MODEL: str = "gemma-4-31b-it"
    GOOGLE_GEMMA_MODEL: str = "models/gemma-4-31b-it" 
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it" # Update with specific gemma4 slug when available

    # TikTok / Apify Config
    APIFY_ACTOR_TIKTOK: str = "clockworks/tiktok-scraper"
    APIFY_TIMEOUT_SECONDS: Annotated[int, BeforeValidator(empty_str_to_none)] = 300
    
    # Ingestion Constraints
    VIDEO_MIN_PLAYS: Annotated[int, BeforeValidator(empty_str_to_none)] = 5000
    VIDEO_MIN_SHARES: Annotated[int, BeforeValidator(empty_str_to_none)] = 50
    VIDEO_MAX_PER_RUN: Annotated[int, BeforeValidator(empty_str_to_none)] = 5
    
    # Stream Config
    STREAM_RAW_POSTS: str = "osint:raw_posts"
    STREAM_NORMALIZED_POSTS: str = "osint:normalized_posts"


@lru_cache
def get_settings() -> Settings:
    """ Cached reads .env once at startup """
    return Settings()

# Global settings instance
settings = get_settings()
