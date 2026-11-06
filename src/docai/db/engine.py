"""SQLAlchemy engines for the ops database: one pooled engine per URL, and the Azure variant that logs in with an Entra token.

Azure Database for PostgreSQL (Entra-only auth): the user is the managed identity's name and the password is an access token for https://ossrdbms-aad.database.windows.net, fetched for every new pooled connection (tokens live 5-60 minutes, so the pool recycles connections after 25). Not run against Azure: see docs/build-status.md."""
from __future__ import annotations

import os
import threading
from typing import Any

from sqlalchemy import Engine, create_engine, event

from docai.core.settings import Database

TOKEN_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"
_ENGINES: dict[str, Engine] = {}
_LOCK = threading.Lock()


def _create(url: str, **kw: Any) -> Engine:
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)  # timestamps are read back in UTC
    kw.setdefault("connect_args", {})["options"] = "-c timezone=UTC"
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20, **kw)


def default_credential():
    """The managed identity of the container (AZURE_CLIENT_ID names the user-assigned one), else whatever DefaultAzureCredential finds."""
    from azure.identity import (  # the `azure` extra
        DefaultAzureCredential,
        ManagedIdentityCredential,
    )

    if os.environ.get("IDENTITY_ENDPOINT"):  # set by Container Apps
        return ManagedIdentityCredential(client_id=os.environ.get("AZURE_CLIENT_ID"))
    return DefaultAzureCredential()


def entra_engine(db: Database, credential: Any = None) -> Engine:
    cred = credential or default_credential()
    engine = _create(db.sqlalchemy_url, pool_recycle=1500, connect_args={"sslmode": "require"})

    @event.listens_for(engine, "do_connect")
    def _token_as_password(dialect, conn_rec, cargs, cparams):
        cparams["password"] = cred.get_token(TOKEN_SCOPE).token

    return engine


def engine_for(db: Database | str) -> Engine:
    """The shared engine for a database setting (or a plain URL). Entra engines are shared per server, name and user."""
    if isinstance(db, str):
        db = Database(url=db)
    key = f"entra:{db.host}/{db.name}/{db.user}" if db.entra_auth else db.url.replace("postgresql://", "postgresql+psycopg://", 1)
    with _LOCK:
        if key not in _ENGINES:
            _ENGINES[key] = entra_engine(db) if db.entra_auth else _create(db.url)
        return _ENGINES[key]
