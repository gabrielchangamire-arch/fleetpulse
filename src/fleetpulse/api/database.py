"""Async SQLAlchemy lifecycle and request-scoped sessions."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_database(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"command_timeout": 5},
    )
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def session_dependency(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session
