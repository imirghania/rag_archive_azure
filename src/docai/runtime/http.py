"""Shared plumbing of the HTTP apps: the validated principal, JSON errors, and serving."""
from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from docai.security.access import Principal
from docai.security.auth import AuthError
from docai.security.tokens import bearer_token

from .context import Context

log = logging.getLogger("docai.runtime.http")


def make_principal_dep(ctx: Context) -> Callable[..., Principal]:
    def principal(token: str = Depends(bearer_token)) -> Principal:
        try:
            return ctx.identity.validate(token)  # type: ignore[attr-defined]
        except AuthError as e:
            raise HTTPException(401, str(e)) from e
    return principal


def new_app(title: str) -> FastAPI:
    app = FastAPI(title=title, docs_url=None, redoc_url=None)

    @app.exception_handler(PermissionError)
    async def _forbidden(_: Request, e: PermissionError):
        return JSONResponse({"error": "forbidden", "detail": str(e)}, status_code=403)

    @app.exception_handler(KeyError)
    async def _missing(_: Request, e: KeyError):
        return JSONResponse({"error": "not_found", "detail": str(e)}, status_code=404)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app
