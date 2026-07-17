"""Shared worker and relay configuration."""

from __future__ import annotations

import socket
from uuid import uuid4

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLEETPULSE_", extra="ignore")

    database_url: str
    redis_url: str = "redis://redis:6379/0"
    telemetry_stream: str = "fleetpulse:telemetry"
    dead_letter_stream: str = "fleetpulse:telemetry:dlq"
    consumer_group: str = "fleetpulse-workers"
    consumer_name: str = Field(default_factory=lambda: f"{socket.gethostname()}-{str(uuid4())[:8]}")
    relay_poll_seconds: float = Field(default=0.5, gt=0)
    reclaim_idle_ms: int = Field(default=2000, ge=100)
    max_delivery_attempts: int = Field(default=3, ge=1)
    cpu_incident_threshold: float = Field(default=90.0, ge=0, le=100)
    memory_incident_threshold: float = Field(default=90.0, ge=0, le=100)
    log_level: str = "INFO"
    metrics_port: int = Field(default=9101, ge=1, le=65535)
