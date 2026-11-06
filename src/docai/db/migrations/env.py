"""Alembic environment. An engine in `config.attributes["engine"]` (docai.devtools.bootstrap passes one, with Entra login in Azure) wins;
otherwise the URL is read from `-x url=...`, then `sqlalchemy.url` in the config, then DOCAI_DATABASE__URL."""
from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine, pool

from docai.db.tables import SCHEMA, metadata

config = context.config


def _url() -> str:
    url = (
        context.get_x_argument(as_dictionary=True).get("url") or 
        config.get_main_option("sqlalchemy.url") or 
        os.environ.get("DOCAI_DATABASE__URL")
        )
    if not url:
        raise SystemExit("no database URL: pass -x url=postgresql+psycopg://... or set DOCAI_DATABASE__URL")
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def _only_ops(name, type_, parent_names):  # the version table and anything else outside `ops` is not ours to compare
    return name == SCHEMA if type_ == "schema" else True


if context.is_offline_mode():
    context.configure(url=_url(), literal_binds=True, target_metadata=metadata, include_schemas=True, include_name=_only_ops)
    with context.begin_transaction():
        context.run_migrations()
else:
    injected = config.attributes.get("engine")
    engine = injected or create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, include_schemas=True, include_name=_only_ops)
        with context.begin_transaction():
            context.run_migrations()
    if not injected:
        engine.dispose()
