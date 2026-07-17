"""Exercise authenticated idempotent ingestion against a running local API."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from uuid import UUID

import httpx

from fleetpulse.telemetry import (
    DiskTelemetry,
    MemoryTelemetry,
    NetworkTelemetry,
    TelemetryBatch,
    TelemetrySample,
)

SMOKE_BATCH_ID = UUID("00000000-0000-4000-8000-000000000001")


def smoke_batch() -> TelemetryBatch:
    return TelemetryBatch(
        batch_id=SMOKE_BATCH_ID,
        agent_id="phase1-smoke-agent",
        hostname="phase1-smoke-host",
        samples=[
            TelemetrySample(
                observed_at=datetime.now(UTC),
                cpu_percent=12.5,
                load_1m=0.1,
                load_5m=0.2,
                load_15m=0.3,
                memory=MemoryTelemetry(
                    total_bytes=1024,
                    available_bytes=512,
                    used_bytes=512,
                    used_percent=50,
                ),
                disks=[
                    DiskTelemetry(
                        mount="/",
                        total_bytes=2048,
                        used_bytes=1024,
                        free_bytes=1024,
                        used_percent=50,
                    )
                ],
                network=NetworkTelemetry(
                    bytes_sent=10,
                    bytes_received=20,
                    packets_sent=1,
                    packets_received=2,
                    errors_in=0,
                    errors_out=0,
                    drops_in=0,
                    drops_out=0,
                    tcp_established=1,
                    tcp_listening=1,
                    tcp_other=0,
                    udp_sockets=0,
                ),
                process_count=1,
                top_processes=[],
            )
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", required=True)
    arguments = parser.parse_args()

    headers = {
        "Authorization": f"Bearer {arguments.token}",
        "X-Request-ID": "phase1-smoke-correlation",
    }
    with httpx.Client(base_url=arguments.api_url, headers=headers, timeout=5) as client:
        unauthorized = client.get("/v1/fleet/agents", headers={"Authorization": ""})
        first = client.post("/v1/telemetry/batches", json=smoke_batch().model_dump(mode="json"))
        second = client.post("/v1/telemetry/batches", json=smoke_batch().model_dump(mode="json"))
        agents = client.get("/v1/fleet/agents")

    assert unauthorized.status_code == 401
    first.raise_for_status()
    second.raise_for_status()
    agents.raise_for_status()
    first_payload = first.json()
    second_payload = second.json()
    agent_payload = agents.json()
    assert first_payload["status"] in {"accepted", "duplicate"}
    assert second_payload["status"] == "duplicate"
    smoke_agent = next(item for item in agent_payload if item["agent_id"] == "phase1-smoke-agent")
    assert smoke_agent["batch_count"] == 1
    assert first.headers["X-Request-ID"] == "phase1-smoke-correlation"

    print(
        json.dumps(
            {
                "authentication_boundary": "passed",
                "first_status": first_payload["status"],
                "replay_status": second_payload["status"],
                "durable_batch_count": smoke_agent["batch_count"],
                "correlation_id": first.headers["X-Request-ID"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
