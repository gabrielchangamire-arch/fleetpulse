"""Phase 1 ingestion and fleet-read routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from fleetpulse.api.database import session_dependency
from fleetpulse.api.models import AgentRecord, OutboxEventRecord, TelemetryBatchRecord
from fleetpulse.api.security import require_agent_token
from fleetpulse.logging import correlation_id
from fleetpulse.telemetry import IngestionResponse, TelemetryBatch

router = APIRouter()
Session = Annotated[AsyncSession, Depends(session_dependency)]
Authenticated = Annotated[None, Depends(require_agent_token)]


class AgentSummary(BaseModel):
    agent_id: str
    hostname: str
    first_seen_at: datetime
    last_seen_at: datetime
    batch_count: int


@router.get("/livez", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/readyz", tags=["health"])
async def readiness(session: Session) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.post(
    "/v1/telemetry/batches",
    response_model=IngestionResponse,
    status_code=202,
    dependencies=[Depends(require_agent_token)],
    tags=["telemetry"],
)
async def ingest_batch(batch: TelemetryBatch, session: Session) -> IngestionResponse:
    now = datetime.now(UTC)
    payload = batch.model_dump(mode="json")
    observed_times = [sample.observed_at for sample in batch.samples]

    async with session.begin():
        agent_statement = postgres_insert(AgentRecord).values(
            agent_id=batch.agent_id,
            hostname=batch.hostname,
            first_seen_at=now,
            last_seen_at=now,
        )
        await session.execute(
            agent_statement.on_conflict_do_update(
                index_elements=[AgentRecord.agent_id],
                set_={"hostname": batch.hostname, "last_seen_at": now},
            )
        )

        batch_statement = (
            postgres_insert(TelemetryBatchRecord)
            .values(
                batch_id=batch.batch_id,
                agent_id=batch.agent_id,
                schema_version=batch.schema_version,
                observed_start=min(observed_times),
                observed_end=max(observed_times),
                sample_count=len(batch.samples),
                payload=payload,
            )
            .on_conflict_do_nothing(index_elements=[TelemetryBatchRecord.batch_id])
            .returning(TelemetryBatchRecord.batch_id)
        )
        inserted = (await session.execute(batch_statement)).scalar_one_or_none()
        outcome: Literal["accepted", "duplicate"] = "duplicate" if inserted is None else "accepted"
        if inserted is not None:
            session.add(
                OutboxEventRecord(
                    aggregate_type="telemetry_batch",
                    aggregate_id=str(batch.batch_id),
                    event_type="telemetry.batch.accepted.v1",
                    payload={"batch_id": str(batch.batch_id), "agent_id": batch.agent_id},
                )
            )

    return IngestionResponse(
        batch_id=batch.batch_id,
        status=outcome,
        request_id=correlation_id.get(),
    )


@router.get(
    "/v1/fleet/agents",
    response_model=list[AgentSummary],
    dependencies=[Depends(require_agent_token)],
    tags=["fleet"],
)
async def list_agents(session: Session) -> list[AgentSummary]:
    statement = (
        select(
            AgentRecord.agent_id,
            AgentRecord.hostname,
            AgentRecord.first_seen_at,
            AgentRecord.last_seen_at,
            func.count(TelemetryBatchRecord.batch_id).label("batch_count"),
        )
        .outerjoin(TelemetryBatchRecord, TelemetryBatchRecord.agent_id == AgentRecord.agent_id)
        .group_by(AgentRecord.agent_id)
        .order_by(AgentRecord.agent_id)
    )
    rows = (await session.execute(statement)).all()
    return [AgentSummary.model_validate(row._mapping) for row in rows]
