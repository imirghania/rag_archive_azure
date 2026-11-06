import hashlib
import json
from pathlib import Path

import pytest

from docai.app.wiring import build_context
from docai.contracts import keys, messageids
from docai.devtools.samples import generate
from docai.runtime.messaging import envelope, send
from docai.core.settings import Settings

FIN_READERS = "11111111-1111-1111-1111-111111111111"
FIN_EXPERTS = "22222222-2222-2222-2222-222222222222"
FIN_STEWARDS = "33333333-3333-3333-3333-333333333333"
FIN_TREASURY = "44444444-4444-4444-4444-444444444444"
HR_READERS = "55555555-5555-5555-5555-555555555555"


@pytest.fixture(scope="session")
def samples(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("samples")
    generate(out)
    return out


ROOT = Path(__file__).resolve().parents[1]


def alembic_config(url: str):
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


@pytest.fixture(scope="session")
def pg_url():
    """Superuser URL of a PostgreSQL 16 with the schema migrated to head. Starts a throwaway container (random port, unique name,
    removed at the end), or uses the server in DOCAI_TEST_DATABASE_URL, whose `ops` tables the tests then empty."""
    import os
    import uuid

    from alembic import command

    from docai.devtools import pg

    url = os.environ.get("DOCAI_TEST_DATABASE_URL")
    name = None
    if not url:
        pg.require_docker()
        name = f"docai-pg-test-{uuid.uuid4().hex[:8]}"
        url = pg.start(name, fast=True)
    try:
        command.upgrade(alembic_config(url), "head")
        yield url
    finally:
        if name:
            pg.stop(name)


@pytest.fixture
def ctx(tmp_path, samples, pg_url):
    settings = Settings(_env_file=None, adapters="local", local_fixtures_dir=samples / "fixtures", local_dir=tmp_path, database={"url": pg_url})
    c = build_context(settings, root=tmp_path)
    c.ops.reset_for_tests()  # truncate and restart the counters: much faster than a new database per test
    for code, name in (("FIN", "Finance"), ("HR", "Human Resources")):
        c.ops.add_department(code, name)
    for gid, dept, kind, name in [(FIN_READERS, "FIN", "reader", "fin-readers"), (FIN_EXPERTS, "FIN", "expert", "fin-experts"),
                                  (FIN_STEWARDS, "FIN", "steward", "fin-stewards"), (FIN_TREASURY, "FIN", "restricted", "fin-treasury"),
                                  (HR_READERS, "HR", "reader", "hr-readers")]:
        c.ops.add_access_group(gid, dept, kind, name)
    c.samples = samples  # type: ignore[attr-defined]
    return c


@pytest.fixture
def as_role(ctx):
    """A store that runs as a login user who is a member of the given database role, the way a service identity runs in Azure."""
    from sqlalchemy import text
    from sqlalchemy.engine import make_url

    from docai.adapters.sql.ops import SqlOps

    admin, made = ctx.ops, []  # `admin` stays the superuser store even when a test swaps ctx.ops

    def make(role: str):
        user = f"u_{role}_test"
        with admin.engine.begin() as c:
            c.execute(text(f"DROP ROLE IF EXISTS {user}"))
            c.execute(text(f"CREATE ROLE {user} LOGIN PASSWORD 'pw' IN ROLE {role}"))
        url = make_url(admin.url.replace("postgresql://", "postgresql+psycopg://", 1)).set(username=user, password="pw")
        made.append(SqlOps(url.render_as_string(hide_password=False), admin.clock))
        return made[-1]

    yield make
    for ops in made:
        ops.engine.dispose()  # a pooled connection of the user would block DROP ROLE
        with admin.engine.begin() as c:
            c.execute(text(f"DROP ROLE IF EXISTS {ops.engine.url.username}"))


def upload(ctx, dossier_id: str, *, only: list[str] | None = None, revision_dir: str | None = None) -> str:
    """Plays job-upload-commit: copies the files into `raw`, writes dossier.json last and sends dossier.received."""
    src = ctx.samples / "dossiers" / dossier_id
    manifest = json.loads((src / "dossier.json").read_text())
    if only is not None:
        manifest["files"] = [f for f in manifest["files"] if f["name"] in only]
    base = revision_dir or keys.raw_dossier_dir(dossier_id, 1)
    for f in manifest["files"]:
        ctx.blobs.write("raw", base + f["name"], (src / f["name"]).read_bytes())
    data = json.dumps(manifest, indent=1).encode()
    ctx.blobs.write("raw", base + "dossier.json", data)
    h = hashlib.sha256(data).hexdigest()
    env = envelope("dossier.received", dossier_id, department=keys.department_of(dossier_id), dossier_id=dossier_id,
                   payload={"manifest": base + "dossier.json", "manifest_hash": h, "source": "upload"})
    send(ctx, env, message_id=messageids.intake(dossier_id, h))
    return h
