"""The signed-in user's bearer token: parsed from the request, and carried to the downstream apps of one request."""
from __future__ import annotations

from contextvars import ContextVar

from fastapi import HTTPException, Request

current_token: ContextVar[str | None] = ContextVar("current_token", default=None)  # the signed-in user's token for this request


def bearer_token(request: Request) -> str:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    return h[7:]
