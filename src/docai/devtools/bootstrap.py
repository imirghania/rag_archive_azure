"""Data-plane setup that the Azure CLI cannot do: the database schema (Alembic), the database users of the managed identities,
the department registry and settings, and the Search indexes and synonym maps.

    uv run python -m docai.devtools.bootstrap all
    uv run python -m docai.devtools.bootstrap migrate        # DOCAI_DATABASE__URL, or the local default

Everything is idempotent. Against Azure (DOCAI_DATABASE__ENTRA_AUTH=true) it signs in with your `az login` identity, which must be
the Entra administrator of the PostgreSQL server; pass `--user` with that administrator's name (the server's role name for it).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from docai.core import catalog
from docai.core.settings import Settings
from docai.db import grants
from docai.db import tables as T
from docai.db.engine import engine_for, entra_engine
from docai.resources import searchdefs

ROOT = Path(__file__).resolve().parents[3]
STATE_FILE = ROOT / ".local" / "deploy.json"  # written by `python -m deploy`


def read_state() -> dict[str, str]:
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}


def admin_engine(settings: Settings, state: dict[str, str], user: str | None = None, database: str | None = None) -> Engine:
    """Local: the single database user of DOCAI_DATABASE__URL. Azure: the signed-in `az` identity as Entra administrator."""
    db = settings.database
    if not db.entra_auth:
        return engine_for(db)
    from azure.identity import AzureCliCredential

    db = db.model_copy(update={"host": db.host or state.get("DB_HOST", ""), "user": user or db.user,
                               **({"name": database} if database else {})})
    if not db.host or not db.user:
        raise SystemExit("no database server or administrator: set DOCAI_DATABASE__HOST and pass --user <your Entra admin name> "
                         "(run deploy step 20 first)")
    return entra_engine(db, AzureCliCredential())


def migrate(engine: Engine) -> None:
    """`alembic upgrade head` on this engine (the schema, the roles, their grants, row-level security)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["engine"] = engine
    command.upgrade(cfg, "head")
    print("database schema is at head")


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def create_service_users(engine: Engine, settings: Settings, state: dict[str, str], directory_engine: Engine | None = None) -> None:
    """Locally the one database user plays every role, so this only makes sure the roles exist.

    On Azure Database for PostgreSQL (Entra auth) each managed identity becomes a database role through the extension function
    `pgaadauth_create_principal_with_oid(roleName, objectId, objectType, isAdmin, isMfa)`, then joins the component's `r_*` role.
    Function name, arguments and the 'service' object type follow Microsoft Learn ("Manage Microsoft Entra Roles in Azure Database for
    PostgreSQL", checked 2026-11-05). NOT RUN against Azure: no server was available. The role name must equal the identity's
    display name, and the object ID is the identity's principal (object) ID, not its client ID: the state file key is OID_<name>.

    The extension `pgaadauth` is installed by the platform only in the `postgres` database (found on the first real run, doubt D47),
    not in `docai`. Roles are shared by the whole server, so the function runs on `directory_engine` (a connection to `postgres`)
    and the check and the GRANT run on `engine`. Without `directory_engine` (local database) both are the same engine."""
    directory = directory_engine or engine
    with engine.begin() as c:
        for stmt in grants.role_statements():
            c.execute(text(stmt))
    if not settings.database.entra_auth:
        print("local database: roles ensured, no per-identity users needed")
        return
    for comp in catalog.COMPONENTS:
        if not comp.sql_role:
            continue
        oid = state.get("OID_" + comp.name.replace("-", "_"))
        if not oid:
            print(f"skip {comp.identity}: no object ID in {STATE_FILE} (run deploy step 10)")
            continue
        with engine.begin() as c:
            missing = not c.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :n"), {"n": comp.identity}).first()
        if missing:
            with directory.begin() as d:
                d.execute(text("SELECT * FROM pg_catalog.pgaadauth_create_principal_with_oid(:n, :oid, 'service', false, false)"),
                          {"n": comp.identity, "oid": oid})
        with engine.begin() as c:
            c.execute(text(f"GRANT {comp.sql_role} TO {_q(comp.identity)}"))
        print(f"database user {comp.identity} -> {comp.sql_role}")


GROUP_SEED = [  # state key, department, kind, name
    ("GROUP_FIN_READERS", "FIN", "reader", "grp-docai-fin-readers"),
    ("GROUP_FIN_EXPERTS", "FIN", "expert", "grp-docai-fin-experts"),
    ("GROUP_FIN_STEWARDS", "FIN", "steward", "grp-docai-fin-stewards"),
    ("GROUP_FIN_TREASURY", "FIN", "restricted", "grp-docai-fin-treasury"),
    ("GROUP_HR_READERS", "HR", "reader", "grp-docai-hr-readers"),
    ("GROUP_HR_EXPERTS", "HR", "expert", "grp-docai-hr-experts"),
    ("GROUP_HR_STEWARDS", "HR", "steward", "grp-docai-hr-stewards"),
]


def seed_registry(engine: Engine, settings: Settings, state: dict[str, str], groups: list[tuple[str, str, str, str]] | None = None) -> None:
    """Departments, access groups and the default tuning and model rows; existing rows are left alone."""
    with engine.begin() as c:
        for code, name in (("FIN", "Finance"), ("HR", "Human Resources")):
            c.execute(pg_insert(T.departments).values(code=code, name=name).on_conflict_do_nothing())
        for key, dept, kind, name in groups or [(state.get(k, ""), d, kd, n) for k, d, kd, n in GROUP_SEED]:
            if not key:
                print(f"skip group {name}: no ID (run deploy step 41)")
                continue
            c.execute(pg_insert(T.access_groups).values(group_id=key, department=dept, kind=kind, name=name).on_conflict_do_nothing())
        rows = {k: json.dumps(v) for k, v in settings.tuning.model_dump().items()}
        rows |= {f"models.{role}": json.dumps(dep) for role, dep in settings.models.model_dump().items()}
        for k, v in rows.items():
            c.execute(pg_insert(T.settings).values(key=k, value=v, updated_by="bootstrap").on_conflict_do_nothing())
    print("registry and settings seeded")


# ---- search -----------------------------------------------------------------------------------
def _search_token() -> str:
    from azure.identity import AzureCliCredential  # type: ignore

    return AzureCliCredential().get_token("https://search.azure.com/.default").token


def _put(endpoint: str, path: str, body: dict, token: str) -> None:
    req = urllib.request.Request(f"{endpoint}{path}?api-version={searchdefs.API_VERSION}", method="PUT",
                                 data=json.dumps(body).encode(), headers={
                                     "Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"PUT {path} failed: {e.code} {e.read().decode()[:500]}") from e


def setup_search(settings: Settings, state: dict[str, str]) -> None:
    endpoint = (settings.azure.search_endpoint or state.get("SEARCH_ENDPOINT", "")).rstrip("/")
    if not endpoint:
        raise SystemExit("no search endpoint: run deploy step 20 first")
    token = _search_token()
    for m in searchdefs.synonym_maps():
        _put(endpoint, f"/synonymmaps/{m['name']}", m, token)
        print("synonym map", m["name"])
    for which in ("docs", "notes"):
        d = searchdefs.index_definition(which, settings.models.embedding_dimensions)
        _put(endpoint, f"/indexes/{d['name']}", d, token)
        print("index", d["name"])


def setup_agent(settings: Settings, state: dict[str, str]) -> None:
    """Creates a new version of the Foundry answer agent when the model, the instructions or the tools changed."""
    from azure.ai.projects import AIProjectClient
    from azure.identity import AzureCliCredential

    from docai.adapters.azure.agent import ensure_agent

    endpoint = settings.azure.foundry_project_endpoint or state.get("FOUNDRY_PROJECT_ENDPOINT", "")
    if not endpoint:
        raise SystemExit("no Foundry project endpoint: run deploy step 30 first")
    print("agent definition", ensure_agent(AIProjectClient(endpoint=endpoint, credential=AzureCliCredential()), settings))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["migrate", "users", "seed", "search", "agent", "all"])
    ap.add_argument("--user", help="Azure: the database role of the Entra administrator you are signed in as")
    args = ap.parse_args(argv)
    settings, state = Settings(), read_state()
    if args.what in ("migrate", "users", "seed", "all"):
        engine = admin_engine(settings, state, args.user)
        if args.what in ("migrate", "all"):
            migrate(engine)
        if args.what in ("users", "all"):
            create_service_users(engine, settings, state, admin_engine(settings, state, args.user, database="postgres"))
        if args.what in ("seed", "all"):
            seed_registry(engine, settings, state)
    if args.what in ("search", "all"):
        setup_search(settings, state)
    if args.what in ("agent", "all"):
        setup_agent(settings, state)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
