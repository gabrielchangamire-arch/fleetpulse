"""API application-boundary tests that do not substitute for PostgreSQL integration."""

from fastapi import Request, Response
from pydantic import SecretStr
from starlette.types import Scope

from fleetpulse.api.app import create_app
from fleetpulse.api.config import ApiSettings
from fleetpulse.api.middleware import correlation_middleware


def test_application_metadata() -> None:
    settings = ApiSettings(
        database_url="postgresql+asyncpg://unused@127.0.0.1/unused",
        agent_token=SecretStr("unit-test-token"),
    )
    application = create_app(settings)
    assert application.title.startswith("FleetPulse")


async def test_correlation_header_is_propagated() -> None:
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/livez",
        "headers": [(b"x-request-id", b"unit-correlation")],
        "query_string": b"",
        "server": ("test", 80),
        "client": ("test", 123),
        "scheme": "http",
        "http_version": "1.1",
        "root_path": "",
    }
    request = Request(scope)

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await correlation_middleware(request, call_next)
    assert response.headers["X-Request-ID"] == "unit-correlation"
