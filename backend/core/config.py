# core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf-8",
        case_sensitive=False,
    )

    POSTGRES_URL:str
    QDRANT_URL:str
    REDIS_URL:str
    GEMINI_API_KEY: str
    APIFY_TOKEN: str
    APIFY_ACTOR_TIKTOK: str 
    APIFY_TIMEOUT_SECONDS:int
    TAVILY_API_KEY: str
    GOOGLE_VISION_API_KEY: str 
    STREAM_RAW_POSTS:str 
    STREAM_NORMALIZED_POSTS:str 
    GOOGLE_APPLICATION_CREDENTIALS:str


settings = Settings()

@lru_cache

def get_settings() -> Settings:
    """ Cached reads .env once at startup """
    return Settings()