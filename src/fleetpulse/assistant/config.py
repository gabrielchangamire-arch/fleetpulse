"""Configuration for the optional assistant service."""

from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AssistantSettings(BaseSettings):
    """Assistant settings, intentionally separate from operational credentials."""

    model_config = SettingsConfigDict(env_prefix="FLEETPULSE_ASSISTANT_", extra="ignore")

    provider: Literal["offline", "openai"] = "offline"
    api_key: SecretStr | None = None
    model: str = "gpt-5-mini"
    request_timeout_seconds: float = 20.0
    max_retries: int = 2
    log_level: str = "INFO"

    @model_validator(mode="after")
    def require_key_for_openai(self) -> "AssistantSettings":
        """Fail closed instead of silently falling back when OpenAI was selected."""
        if self.provider == "openai" and (
            self.api_key is None or not self.api_key.get_secret_value()
        ):
            raise ValueError("FLEETPULSE_ASSISTANT_API_KEY is required for provider=openai")
        return self
