"""Phase 1 ingestion and fleet-read routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from fleetpulse.api.database import session_dependency
from fleetpulse.api.models import (
    AgentRecord,
    DeploymentRecord,
    FleetStateRecord,
    IncidentRecord,
    OutboxEventRecord,
    TelemetryBatchRecord,
)
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


class IncidentView(BaseModel):
    incident_id: UUID
    agent_id: str
    incident_type: str
    status: str
    severity: str
    summary: str
    evidence: dict[str, object]
    opened_at: datetime


class DeploymentCreate(BaseModel):
    service: str
    version: str
    status: str = "recorded"
    requested_by: str


class DeploymentView(DeploymentCreate):
    deployment_id: UUID
    created_at: datetime


class FleetStateView(BaseModel):
    agent_id: str
    last_batch_id: UUID
    observed_at: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float


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


@router.get(
    "/v1/fleet/state",
    response_model=list[FleetStateView],
    dependencies=[Depends(require_agent_token)],
    tags=["fleet"],
)
async def list_fleet_state(session: Session) -> list[FleetStateView]:
    rows = (
        await session.execute(select(FleetStateRecord).order_by(FleetStateRecord.agent_id))
    ).scalars()
    return [FleetStateView.model_validate(row, from_attributes=True) for row in rows]


@router.get(
    "/v1/incidents",
    response_model=list[IncidentView],
    dependencies=[Depends(require_agent_token)],
    tags=["incidents"],
)
async def list_incidents(session: Session) -> list[IncidentView]:
    rows = (
        await session.execute(select(IncidentRecord).order_by(IncidentRecord.opened_at))
    ).scalars()
    return [IncidentView.model_validate(row, from_attributes=True) for row in rows]


@router.post(
    "/v1/deployments",
    response_model=DeploymentView,
    status_code=201,
    dependencies=[Depends(require_agent_token)],
    tags=["deployments"],
)
async def create_deployment(payload: DeploymentCreate, session: Session) -> DeploymentView:
    deployment = DeploymentRecord(deployment_id=uuid4(), **payload.model_dump())
    async with session.begin():
        session.add(deployment)
    await session.refresh(deployment)
    return DeploymentView.model_validate(deployment, from_attributes=True)


@router.get(
    "/v1/deployments",
    response_model=list[DeploymentView],
    dependencies=[Depends(require_agent_token)],
    tags=["deployments"],
)
async def list_deployments(session: Session) -> list[DeploymentView]:
    rows = (
        await session.execute(select(DeploymentRecord).order_by(DeploymentRecord.created_at))
    ).scalars()
    return [DeploymentView.model_validate(row, from_attributes=True) for row in rows]
