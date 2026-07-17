"""Alembic environment using the same async PostgreSQL driver as the API."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

import asyncpg
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from fleetpulse.api.models import Base

configuration = context.config
if configuration.config_file_name is not None:
    fileConfig(configuration.config_file_name)

database_url = os.environ.get("FLEETPULSE_DATABASE_URL")
if not database_url:
    raise RuntimeError("FLEETPULSE_DATABASE_URL is required for migrations")
configuration.set_main_option("sqlalchemy.url", database_url)
target_metadata = Base.metadata
MIGRATION_LOCK_ID = 527_644_501_933_021


def run_migrations_offline() -> None:
    context.configure(
        url=configuration.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        configuration.get_section(configuration.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    lock_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    lock_connection = await asyncpg.connect(lock_url)
    try:
        await lock_connection.execute("SELECT pg_advisory_lock($1)", MIGRATION_LOCK_ID)
        async with connectable.connect() as connection:
            await connection.run_sync(run_sync_migrations)
    finally:
        await lock_connection.execute("SELECT pg_advisory_unlock($1)", MIGRATION_LOCK_ID)
        await lock_connection.close()
        await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
