"""Create durable Phase 1 ingestion tables.

Revision ID: 20260717_0001
Revises:
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_table(
        "telemetry_batches",
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("observed_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.agent_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("batch_id"),
    )
    op.create_index(
        "ix_telemetry_batches_agent_received",
        "telemetry_batches",
        ["agent_id", "received_at"],
    )
    op.create_table(
        "outbox_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publication_attempts", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_outbox_unpublished", "outbox_events", ["published_at", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_unpublished", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_telemetry_batches_agent_received", table_name="telemetry_batches")
    op.drop_table("telemetry_batches")
    op.drop_table("agents")
