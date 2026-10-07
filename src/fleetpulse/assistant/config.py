"""Configuration for the optional assistant service."""

from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AssistantSettings(BaseSettings):
    """Assistant settings, intentionally separate from operational credentials."""

    model_config = SettingsConfigDict(env_prefix="FLEETPULSE_ASSISTANT_", extra="ignore")

    provider: Literal["offline", "openai"] = "offline"
    api_key: SecretStr | None = None
    model: str = "gpt-5-mini"
    request_timeout_seconds: float = Field(default=20.0, gt=0, le=60)
    max_retries: int = Field(default=2, ge=0, le=3)
    max_output_tokens: int = Field(default=2000, ge=128, le=8000)
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)
    log_level: str = "INFO"

    @model_validator(mode="after")
    def require_key_for_openai(self) -> "AssistantSettings":
        """Fail closed instead of silently falling back when OpenAI was selected."""
        if self.provider == "openai" and (
            self.api_key is None or not self.api_key.get_secret_value()
        ):
            raise ValueError("FLEETPULSE_ASSISTANT_API_KEY is required for provider=openai")
        return self
