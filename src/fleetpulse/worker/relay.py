"""Publish transactional PostgreSQL outbox rows to Redis Streams."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import time
from contextlib import suppress
from datetime import UTC, datetime

from prometheus_client import start_http_server
from redis.asyncio import Redis
from sqlalchemy import select

from fleetpulse.api.database import create_database
from fleetpulse.api.models import OutboxEventRecord
from fleetpulse.logging import configure_logging
from fleetpulse.metrics import OUTBOX_FAILURES, OUTBOX_LAST_FAILURE, OUTBOX_PUBLISHED
from fleetpulse.worker.config import WorkerSettings

LOGGER = logging.getLogger("fleetpulse.relay")


async def publish_once(settings: WorkerSettings, redis: Redis) -> int:
    engine, sessions = create_database(settings.database_url)
    published = 0
    try:
        async with sessions() as session, session.begin():
            rows = (
                await session.execute(
                    select(OutboxEventRecord)
                    .where(OutboxEventRecord.published_at.is_(None))
                    .order_by(OutboxEventRecord.created_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            ).scalars()
            for event in rows:
                await redis.xadd(
                    settings.telemetry_stream,
                    {
                        "event_id": str(event.event_id),
                        "event_type": event.event_type,
                        "aggregate_id": event.aggregate_id,
                        "payload": json.dumps(event.payload, separators=(",", ":")),
                    },
                )
                event.published_at = datetime.now(UTC)
                event.publication_attempts += 1
                published += 1
    finally:
        await engine.dispose()
    return published


async def run(settings: WorkerSettings) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=3)
    try:
        while not stop.is_set():
            try:
                count = await publish_once(settings, redis)
                if count:
                    OUTBOX_PUBLISHED.inc(count)
                    LOGGER.info(
                        "outbox events published",
                        extra={"event": "outbox_published", "status": count},
                    )
            except Exception:
                OUTBOX_FAILURES.inc()
                OUTBOX_LAST_FAILURE.set(time.time())
                LOGGER.exception("outbox publication failed", extra={"event": "outbox_failed"})
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=settings.relay_poll_seconds)
    finally:
        await redis.aclose()


def main() -> None:
    settings = WorkerSettings()  # type: ignore[call-arg]
    configure_logging(settings.log_level)
    start_http_server(settings.metrics_port)
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
