"""Telemetry contract and data-minimization tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from fleetpulse.telemetry import (
    DiskTelemetry,
    MemoryTelemetry,
    NetworkTelemetry,
    ProcessTelemetry,
    TelemetryBatch,
    TelemetrySample,
)


def sample() -> TelemetrySample:
    return TelemetrySample(
        observed_at=datetime.now(UTC),
        cpu_percent=10,
        load_1m=0.1,
        load_5m=0.2,
        load_15m=0.3,
        memory=MemoryTelemetry(
            total_bytes=100,
            available_bytes=40,
            used_bytes=60,
            used_percent=60,
        ),
        disks=[
            DiskTelemetry(
                mount="/",
                total_bytes=100,
                used_bytes=50,
                free_bytes=50,
                used_percent=50,
            )
        ],
        network=NetworkTelemetry(
            bytes_sent=1,
            bytes_received=2,
            packets_sent=3,
            packets_received=4,
            errors_in=0,
            errors_out=0,
            drops_in=0,
            drops_out=0,
            tcp_established=1,
            tcp_listening=1,
            tcp_other=0,
            udp_sockets=1,
        ),
        process_count=1,
        top_processes=[ProcessTelemetry(pid=1, name="init", cpu_percent=0, memory_percent=0.1)],
    )


def batch() -> TelemetryBatch:
    return TelemetryBatch(
        batch_id=uuid4(),
        agent_id="test-agent",
        hostname="test-host",
        samples=[sample()],
    )


def test_batch_round_trips_as_versioned_json() -> None:
    original = batch()
    restored = TelemetryBatch.model_validate_json(original.model_dump_json())
    assert restored == original
    assert restored.schema_version == 1


def test_process_contract_forbids_command_line_and_environment() -> None:
    with pytest.raises(ValidationError):
        ProcessTelemetry.model_validate(
            {
                "pid": 1,
                "name": "unsafe",
                "cpu_percent": 1,
                "memory_percent": 1,
                "cmdline": ["--password", "secret"],
            }
        )


def test_sample_rejects_naive_timestamp() -> None:
    payload = sample().model_dump()
    payload["observed_at"] = datetime.now()
    with pytest.raises(ValidationError, match="timezone"):
        TelemetrySample.model_validate(payload)


def test_batch_rejects_invalid_agent_identifier() -> None:
    with pytest.raises(ValidationError):
        TelemetryBatch(
            batch_id=uuid4(),
            agent_id="invalid agent id",
            hostname="host",
            samples=[sample()],
        )
