"""Timeout-bound telemetry delivery and retry scheduling."""

from __future__ import annotations

import random
from collections.abc import Callable

import httpx

from fleetpulse.telemetry import IngestionResponse, TelemetryBatch


def full_jitter_delay(
    attempt: int,
    base_seconds: float,
    cap_seconds: float,
    uniform: Callable[[float, float], float] = random.uniform,
) -> float:
    """Return capped exponential backoff with full jitter."""
    ceiling = min(cap_seconds, base_seconds * (2 ** max(0, attempt)))
    return uniform(0.0, ceiling)


class IngestionClient:
    """HTTP client with explicit deadlines; durable retry state lives in the spool."""

    def __init__(self, api_url: str, token: str, timeout_seconds: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=api_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            headers={"Authorization": f"Bearer {token}"},
        )

    async def send(self, batch: TelemetryBatch) -> IngestionResponse:
        response = await self._client.post(
            "/v1/telemetry/batches",
            content=batch.model_dump_json(),
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": str(batch.batch_id),
            },
        )
        response.raise_for_status()
        return IngestionResponse.model_validate(response.json())

    async def close(self) -> None:
        await self._client.aclose()
