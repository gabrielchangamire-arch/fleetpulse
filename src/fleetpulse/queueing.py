"""Redis Stream contracts shared by the outbox relay and workers."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class QueueEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    event_type: str
    aggregate_id: str
    payload: dict[str, str]
