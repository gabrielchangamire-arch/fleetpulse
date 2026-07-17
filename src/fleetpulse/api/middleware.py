"""Request correlation and structured access logging."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from fleetpulse.logging import correlation_id

LOGGER = logging.getLogger("fleetpulse.api.access")


async def correlation_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Attach a bounded correlation ID and log request completion."""
    request_id = request.headers.get("X-Request-ID", "")[:128] or str(uuid4())
    token = correlation_id.set(request_id)
    started = time.monotonic()
    try:
        response = await call_next(request)
        duration_ms = round((time.monotonic() - started) * 1000, 3)
        response.headers["X-Request-ID"] = request_id
        LOGGER.info(
            "request completed",
            extra={
                "event": "request_completed",
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    finally:
        correlation_id.reset(token)
