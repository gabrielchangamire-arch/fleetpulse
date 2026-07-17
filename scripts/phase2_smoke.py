"""Verify worker-derived fleet, incident, and deployment state through the API."""

from __future__ import annotations

import argparse
import json
import time
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


def high_cpu_batch(batch_id: UUID) -> TelemetryBatch:
    return TelemetryBatch(
        batch_id=batch_id,
        agent_id="phase2-incident-agent",
        hostname="phase2-host",
        samples=[
            TelemetrySample(
                observed_at=datetime.now(UTC),
                cpu_percent=99,
                load_1m=4,
                load_5m=3,
                load_15m=2,
                memory=MemoryTelemetry(
                    total_bytes=100, available_bytes=50, used_bytes=50, used_percent=50
                ),
                disks=[
                    DiskTelemetry(
                        mount="/", total_bytes=100, used_bytes=50, free_bytes=50, used_percent=50
                    )
                ],
                network=NetworkTelemetry(
                    bytes_sent=1,
                    bytes_received=1,
                    packets_sent=1,
                    packets_received=1,
                    errors_in=0,
                    errors_out=0,
                    drops_in=0,
                    drops_out=0,
                    tcp_established=0,
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
    parser.add_argument("--token", required=True)
    parser.add_argument("--batch-id", default="00000000-0000-4000-8000-000000000002")
    args = parser.parse_args()
    headers = {"Authorization": f"Bearer {args.token}", "X-Request-ID": "phase2-smoke"}
    with httpx.Client(base_url="http://127.0.0.1:8000", headers=headers, timeout=5) as client:
        ingest = client.post(
            "/v1/telemetry/batches",
            json=high_cpu_batch(UUID(args.batch_id)).model_dump(mode="json"),
        )
        ingest.raise_for_status()
        deployment = client.post(
            "/v1/deployments",
            json={"service": "api", "version": "phase2", "requested_by": "phase2-smoke"},
        )
        deployment.raise_for_status()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            fleet = client.get("/v1/fleet/state")
            incidents = client.get("/v1/incidents")
            fleet.raise_for_status()
            incidents.raise_for_status()
            state = next(
                (item for item in fleet.json() if item["agent_id"] == "phase2-incident-agent"), None
            )
            incident = next(
                (item for item in incidents.json() if item["agent_id"] == "phase2-incident-agent"),
                None,
            )
            if state and incident:
                print(
                    json.dumps(
                        {
                            "ingestion": ingest.json()["status"],
                            "fleet_cpu": state["cpu_percent"],
                            "incident_type": incident["incident_type"],
                            "deployment_status": deployment.json()["status"],
                        },
                        sort_keys=True,
                    )
                )
                return 0
            time.sleep(0.25)
    raise RuntimeError("worker-derived state did not appear before timeout")


if __name__ == "__main__":
    raise SystemExit(main())
