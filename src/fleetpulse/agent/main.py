"""FleetPulse agent process with graceful shutdown and durable delivery."""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from contextlib import suppress
from datetime import UTC, datetime
from uuid import uuid4

from prometheus_client import start_http_server

from fleetpulse.agent.client import IngestionClient, full_jitter_delay
from fleetpulse.agent.collector import collect_sample
from fleetpulse.agent.config import AgentSettings
from fleetpulse.agent.spool import BatchSpool
from fleetpulse.logging import configure_logging, correlation_id
from fleetpulse.telemetry import TelemetryBatch, TelemetrySample

LOGGER = logging.getLogger("fleetpulse.agent")


async def run(settings: AgentSettings) -> None:
    """Collect until terminated, flushing complete batches into the durable spool."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)

    spool = BatchSpool(
        settings.spool_path,
        max_batches=settings.max_spool_batches,
        max_bytes=settings.max_spool_bytes,
    )
    client = IngestionClient(
        settings.api_url,
        settings.agent_token.get_secret_value(),
        settings.request_timeout_seconds,
        str(settings.ca_bundle) if settings.ca_bundle else None,
    )
    samples: list[TelemetrySample] = []
    try:
        while not stop.is_set():
            samples.append(collect_sample())
            if len(samples) >= settings.batch_size:
                batch = TelemetryBatch(
                    batch_id=uuid4(),
                    agent_id=settings.agent_id,
                    hostname=settings.hostname,
                    samples=samples,
                )
                dropped = spool.enqueue(batch)
                samples = []
                LOGGER.info(
                    "telemetry batch spooled",
                    extra={"event": "batch_spooled", "batch_id": batch.batch_id, "status": "ok"},
                )
                if dropped:
                    LOGGER.error(
                        "spool bound evicted oldest batches",
                        extra={"event": "spool_overflow", "status": "dropped"},
                    )

            pending = spool.next_ready()
            if pending is not None:
                token = correlation_id.set(str(pending.batch.batch_id))
                try:
                    result = await client.send(pending.batch)
                    spool.mark_sent(pending.batch.batch_id)
                    LOGGER.info(
                        "telemetry batch delivered",
                        extra={
                            "event": "batch_delivered",
                            "batch_id": pending.batch.batch_id,
                            "status": result.status,
                            "attempt": pending.attempts + 1,
                        },
                    )
                except Exception as error:
                    delay = full_jitter_delay(
                        pending.attempts,
                        settings.retry_base_seconds,
                        settings.retry_cap_seconds,
                    )
                    spool.mark_failed(
                        pending.batch.batch_id,
                        type(error).__name__,
                        time.time() + delay,
                    )
                    LOGGER.warning(
                        "telemetry delivery failed",
                        extra={
                            "event": "batch_delivery_failed",
                            "batch_id": pending.batch.batch_id,
                            "status": "retrying",
                            "attempt": pending.attempts + 1,
                        },
                    )
                finally:
                    correlation_id.reset(token)

            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=settings.collection_interval_seconds)
    finally:
        if samples:
            spool.enqueue(
                TelemetryBatch(
                    batch_id=uuid4(),
                    agent_id=settings.agent_id,
                    hostname=settings.hostname,
                    samples=samples,
                )
            )
        await client.close()
        spool.close()
        LOGGER.info(
            "agent stopped gracefully",
            extra={"event": "agent_stopped", "status": datetime.now(UTC).isoformat()},
        )


def main() -> None:
    settings = AgentSettings()  # type: ignore[call-arg]
    configure_logging(settings.log_level)
    start_http_server(settings.metrics_port)
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
