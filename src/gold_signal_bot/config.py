"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables.
    The names are case-insensitive and use the same name as the field.
    
    Example:
        ALPHA_VANTAGE_API_KEY=your_key_here
        FETCH_INTERVAL_SECONDS=900
    """
    
    # Alpha Vantage API
    alpha_vantage_api_key: str
    alpha_vantage_base_url: str = "https://www.alphavantage.co/query"
    
    # Rate limiting (free tier: 5 calls/min, 25 calls/day)
    rate_limit_per_minute: int = 5
    rate_limit_per_day: int = 25
    fetch_interval_seconds: int = 900  # 15 minutes default
    
    # Retry configuration for transient failures
    max_retries: int = 3
    retry_backoff_seconds: int = 60
    
    # Telegram Bot settings
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    telegram_parse_mode: str = "HTML"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once
    from environment/file for the lifetime of the application.
    
    Returns:
        Settings: Application configuration instance.
    """
    return Settings()
