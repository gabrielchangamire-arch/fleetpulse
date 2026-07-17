"""FastAPI application factory and lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app
from redis.asyncio import Redis

from fleetpulse.api.config import ApiSettings
from fleetpulse.api.database import create_database
from fleetpulse.api.middleware import correlation_middleware
from fleetpulse.api.routes import router
from fleetpulse.logging import configure_logging


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    resolved_settings = settings or ApiSettings()  # type: ignore[call-arg]
    configure_logging(resolved_settings.log_level)
    engine, session_factory = create_database(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.settings = resolved_settings
        application.state.session_factory = session_factory
        application.state.redis = Redis.from_url(
            resolved_settings.redis_url, decode_responses=True, socket_timeout=1
        )
        yield
        await application.state.redis.aclose()
        await engine.dispose()

    application = FastAPI(
        title="FleetPulse — Linux Fleet Reliability and Incident Response Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.middleware("http")(correlation_middleware)
    application.include_router(router)
    application.mount("/metrics", make_asgi_app())
    return application
