"""Isolated FastAPI entry point for the optional assistant."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status

from fleetpulse.api.middleware import correlation_middleware
from fleetpulse.assistant.config import AssistantSettings
from fleetpulse.assistant.models import (
    AnalysisRequest,
    AnalysisResponse,
    ReviewReceipt,
    ReviewRequest,
)
from fleetpulse.assistant.providers import create_provider
from fleetpulse.assistant.service import (
    AssistantService,
    DuplicateReviewError,
    UnknownProposalError,
)
from fleetpulse.logging import configure_logging


def create_app(settings: AssistantSettings | None = None) -> FastAPI:
    """Create an assistant that has no operational dependencies or credentials."""
    resolved = settings or AssistantSettings()
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> Any:
        application.state.assistant = AssistantService(create_provider(resolved))
        yield

    application = FastAPI(
        title="FleetPulse read-only incident assistant",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.middleware("http")(correlation_middleware)

    @application.get("/livez")
    async def livez() -> dict[str, str]:
        return {"status": "alive"}

    @application.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready", "provider": resolved.provider, "authority": "read-only"}

    @application.post("/v1/analysis", response_model=AnalysisResponse)
    async def analyze(payload: AnalysisRequest, request: Request) -> AnalysisResponse:
        service: AssistantService = request.app.state.assistant
        return await service.analyze(payload)

    @application.post("/v1/reviews", response_model=ReviewReceipt)
    async def review(payload: ReviewRequest, request: Request) -> ReviewReceipt:
        service: AssistantService = request.app.state.assistant
        try:
            return await service.review(payload)
        except UnknownProposalError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except DuplicateReviewError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return application
