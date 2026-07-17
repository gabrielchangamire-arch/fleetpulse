"""Idempotent Redis Stream consumer with reclaim, bounded retry, and DLQ."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import ResponseError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from fleetpulse.api.database import create_database
from fleetpulse.api.models import (
    DeadLetterRecord,
    FleetStateRecord,
    IncidentRecord,
    ProcessedEventRecord,
    TelemetryBatchRecord,
)
from fleetpulse.logging import configure_logging, correlation_id
from fleetpulse.queueing import QueueEvent
from fleetpulse.telemetry import TelemetryBatch
from fleetpulse.worker.config import WorkerSettings

LOGGER = logging.getLogger("fleetpulse.worker")


def decode_event(fields: dict[str, str]) -> QueueEvent:
    return QueueEvent.model_validate(
        {
            "event_id": fields["event_id"],
            "event_type": fields["event_type"],
            "aggregate_id": fields["aggregate_id"],
            "payload": json.loads(fields["payload"]),
        }
    )


async def process_event(settings: WorkerSettings, message_id: str, event: QueueEvent) -> None:
    engine, sessions = create_database(settings.database_url)
    try:
        async with sessions() as session, session.begin():
            inserted = (
                await session.execute(
                    postgres_insert(ProcessedEventRecord)
                    .values(
                        event_id=event.event_id,
                        stream_message_id=message_id,
                        consumer_name=settings.consumer_name,
                    )
                    .on_conflict_do_nothing(index_elements=[ProcessedEventRecord.event_id])
                    .returning(ProcessedEventRecord.event_id)
                )
            ).scalar_one_or_none()
            if inserted is None:
                return
            if event.event_type != "telemetry.batch.accepted.v1":
                raise ValueError(f"unsupported event type: {event.event_type}")
            record = (
                await session.execute(
                    select(TelemetryBatchRecord).where(
                        TelemetryBatchRecord.batch_id == event.aggregate_id
                    )
                )
            ).scalar_one()
            batch = TelemetryBatch.model_validate(record.payload)
            latest = max(batch.samples, key=lambda sample: sample.observed_at)
            disk_percent = max(disk.used_percent for disk in latest.disks)
            await session.execute(
                postgres_insert(FleetStateRecord)
                .values(
                    agent_id=batch.agent_id,
                    last_batch_id=batch.batch_id,
                    observed_at=latest.observed_at,
                    cpu_percent=latest.cpu_percent,
                    memory_percent=latest.memory.used_percent,
                    disk_percent=disk_percent,
                )
                .on_conflict_do_update(
                    index_elements=[FleetStateRecord.agent_id],
                    set_={
                        "last_batch_id": batch.batch_id,
                        "observed_at": latest.observed_at,
                        "cpu_percent": latest.cpu_percent,
                        "memory_percent": latest.memory.used_percent,
                        "disk_percent": disk_percent,
                    },
                )
            )
            conditions = (
                ("high_cpu", latest.cpu_percent, settings.cpu_incident_threshold),
                ("high_memory", latest.memory.used_percent, settings.memory_incident_threshold),
            )
            for incident_type, value, threshold in conditions:
                if value >= threshold:
                    await session.execute(
                        postgres_insert(IncidentRecord)
                        .values(
                            agent_id=batch.agent_id,
                            incident_type=incident_type,
                            deduplication_key=f"{batch.agent_id}:{incident_type}",
                            status="open",
                            severity="warning",
                            summary=f"{incident_type} threshold crossed",
                            evidence={
                                "batch_id": str(batch.batch_id),
                                "value": value,
                                "threshold": threshold,
                            },
                        )
                        .on_conflict_do_nothing(constraint="uq_incident_open_deduplication")
                    )
    finally:
        await engine.dispose()


async def delivery_attempts(redis: Redis, settings: WorkerSettings, message_id: str) -> int:
    pending: Any = await redis.xpending_range(
        settings.telemetry_stream, settings.consumer_group, message_id, message_id, 1
    )
    return int(pending[0]["times_delivered"]) if pending else 1


async def dead_letter(
    redis: Redis,
    settings: WorkerSettings,
    message_id: str,
    fields: dict[str, str],
    error: Exception,
    attempts: int,
) -> None:
    await redis.xadd(
        settings.dead_letter_stream,
        {"source_id": message_id, "error": type(error).__name__, "payload": json.dumps(fields)},
    )
    engine, sessions = create_database(settings.database_url)
    try:
        async with sessions() as session, session.begin():
            await session.execute(
                postgres_insert(DeadLetterRecord)
                .values(
                    stream_message_id=message_id,
                    event_id=fields.get("event_id", "unknown"),
                    error_type=type(error).__name__,
                    attempts=attempts,
                    payload=fields,
                )
                .on_conflict_do_nothing(index_elements=[DeadLetterRecord.stream_message_id])
            )
    finally:
        await engine.dispose()
    await redis.xack(settings.telemetry_stream, settings.consumer_group, message_id)


async def handle_message(
    redis: Redis, settings: WorkerSettings, message_id: str, fields: dict[str, str]
) -> None:
    token = correlation_id.set(fields.get("event_id", message_id))
    try:
        event = decode_event(fields)
        await process_event(settings, message_id, event)
        await redis.xack(settings.telemetry_stream, settings.consumer_group, message_id)
        LOGGER.info(
            "event processed", extra={"event": "event_processed", "status": settings.consumer_name}
        )
    except (ValidationError, KeyError, ValueError, json.JSONDecodeError) as error:
        attempts = await delivery_attempts(redis, settings, message_id)
        if attempts >= settings.max_delivery_attempts:
            await dead_letter(redis, settings, message_id, fields, error, attempts)
            LOGGER.error(
                "event dead-lettered", extra={"event": "event_dead_lettered", "attempt": attempts}
            )
        else:
            LOGGER.warning(
                "event left pending for retry", extra={"event": "event_retry", "attempt": attempts}
            )
    finally:
        correlation_id.reset(token)


async def run(settings: WorkerSettings) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop.set)
    redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=3)
    try:
        try:
            await redis.xgroup_create(
                settings.telemetry_stream, settings.consumer_group, id="0", mkstream=True
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(error):
                raise
        while not stop.is_set():
            claimed: Any = await redis.xautoclaim(
                settings.telemetry_stream,
                settings.consumer_group,
                settings.consumer_name,
                settings.reclaim_idle_ms,
                "0-0",
                count=10,
            )
            for message_id, fields in claimed[1]:
                await handle_message(redis, settings, message_id, fields)
            messages: Any = await redis.xreadgroup(
                settings.consumer_group,
                settings.consumer_name,
                {settings.telemetry_stream: ">"},
                count=10,
                block=500,
            )
            for _, entries in messages:
                for message_id, fields in entries:
                    await handle_message(redis, settings, message_id, fields)
    finally:
        await redis.aclose()


def main() -> None:
    settings = WorkerSettings()  # type: ignore[call-arg]
    configure_logging(settings.log_level)
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
