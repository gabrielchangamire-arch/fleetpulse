"""Constant-time local agent authentication."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, status


async def require_agent_token(request: Request) -> None:
    expected = request.app.state.settings.agent_token.get_secret_value()
    authorization = request.headers.get("Authorization", "")
    scheme, _, supplied = authorization.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid agent credential",
            headers={"WWW-Authenticate": "Bearer"},
        )
