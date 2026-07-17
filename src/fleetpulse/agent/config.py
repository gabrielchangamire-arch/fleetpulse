"""Environment-driven agent configuration."""

from __future__ import annotations

import re
import socket
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def default_agent_id() -> str:
    """Create a schema-safe stable default from the hostname."""
    normalized = re.sub(r"[^a-zA-Z0-9._-]", "-", socket.gethostname())[:128]
    return normalized or "fleetpulse-agent"


class AgentSettings(BaseSettings):
    """Agent settings loaded from `FLEETPULSE_` variables."""

    model_config = SettingsConfigDict(env_prefix="FLEETPULSE_", extra="ignore")

    api_url: str = "http://127.0.0.1:8000"
    ca_bundle: Path | None = None
    agent_token: SecretStr
    agent_id: str = Field(default_factory=default_agent_id)
    hostname: str = Field(default_factory=socket.gethostname)
    spool_path: Path = Path(".fleetpulse/agent-spool.db")
    collection_interval_seconds: float = Field(default=10.0, gt=0)
    batch_size: int = Field(default=6, ge=1, le=100)
    max_spool_batches: int = Field(default=1000, ge=1)
    max_spool_bytes: int = Field(default=64 * 1024 * 1024, ge=1024)
    request_timeout_seconds: float = Field(default=5.0, gt=0)
    retry_base_seconds: float = Field(default=1.0, gt=0)
    retry_cap_seconds: float = Field(default=60.0, gt=0)
    log_level: str = "INFO"
