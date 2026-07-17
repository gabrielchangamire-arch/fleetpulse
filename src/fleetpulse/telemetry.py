"""Versioned telemetry contracts shared by agents and ingestion services."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]
Percentage = Annotated[float, Field(ge=0, le=100)]


class ProcessTelemetry(BaseModel):
    """Non-sensitive process resource information."""

    model_config = ConfigDict(extra="forbid")

    pid: Annotated[int, Field(ge=1)]
    name: Annotated[str, Field(min_length=1, max_length=256)]
    cpu_percent: NonNegativeFloat
    memory_percent: Percentage


class DiskTelemetry(BaseModel):
    """Usage for one filesystem mount."""

    model_config = ConfigDict(extra="forbid")

    mount: Annotated[str, Field(min_length=1, max_length=512)]
    total_bytes: NonNegativeInt
    used_bytes: NonNegativeInt
    free_bytes: NonNegativeInt
    used_percent: Percentage


class MemoryTelemetry(BaseModel):
    """Host memory counters."""

    model_config = ConfigDict(extra="forbid")

    total_bytes: NonNegativeInt
    available_bytes: NonNegativeInt
    used_bytes: NonNegativeInt
    used_percent: Percentage


class NetworkTelemetry(BaseModel):
    """Aggregate network I/O and socket counts."""

    model_config = ConfigDict(extra="forbid")

    bytes_sent: NonNegativeInt
    bytes_received: NonNegativeInt
    packets_sent: NonNegativeInt
    packets_received: NonNegativeInt
    errors_in: NonNegativeInt
    errors_out: NonNegativeInt
    drops_in: NonNegativeInt
    drops_out: NonNegativeInt
    tcp_established: NonNegativeInt
    tcp_listening: NonNegativeInt
    tcp_other: NonNegativeInt
    udp_sockets: NonNegativeInt


class TelemetrySample(BaseModel):
    """One bounded snapshot collected by an agent."""

    model_config = ConfigDict(extra="forbid")

    observed_at: datetime
    cpu_percent: Percentage
    load_1m: NonNegativeFloat
    load_5m: NonNegativeFloat
    load_15m: NonNegativeFloat
    memory: MemoryTelemetry
    disks: Annotated[list[DiskTelemetry], Field(min_length=1, max_length=32)]
    network: NetworkTelemetry
    process_count: NonNegativeInt
    top_processes: Annotated[list[ProcessTelemetry], Field(max_length=20)]

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value


class TelemetryBatch(BaseModel):
    """Idempotent transport unit persisted by the ingestion API."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    batch_id: UUID
    agent_id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")]
    hostname: Annotated[str, Field(min_length=1, max_length=255)]
    samples: Annotated[list[TelemetrySample], Field(min_length=1, max_length=100)]


class IngestionResponse(BaseModel):
    """Stable acknowledgement for accepted and replayed batches."""

    batch_id: UUID
    status: Literal["accepted", "duplicate"]
    request_id: str
