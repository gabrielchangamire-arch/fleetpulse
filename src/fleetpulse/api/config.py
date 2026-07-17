"""Environment-driven API configuration."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """API settings loaded from `FLEETPULSE_` variables."""

    model_config = SettingsConfigDict(env_prefix="FLEETPULSE_", extra="ignore")

    database_url: str
    agent_token: SecretStr
    redis_url: str = "redis://redis:6379/0"
    cache_enabled: bool = True
    cache_ttl_seconds: int = 15
    log_level: str = "INFO"
    environment: str = "development"
