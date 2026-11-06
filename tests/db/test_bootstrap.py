import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import text

from conftest import alembic_config
from docai.db import grants
from docai.db.engine import TOKEN_SCOPE, entra_engine
from docai.devtools import bootstrap
from docai.core.settings import Database, Settings


def test_the_migrations_are_one_unbroken_chain_that_can_also_be_undone():
    script = ScriptDirectory.from_config(alembic_config("postgresql+psycopg://x/x"))
    assert len(script.get_heads()) == 1, "two branches: merge them"
    revs = list(script.walk_revisions())
    assert [r.revision for r in reversed(revs)][:2] == ["0001", "0002"]
    for r in revs:
        assert "def downgrade" in open(r.path).read(), f"{r.revision} must say how to undo itself"


def test_migrate_and_seed_can_run_twice(ctx, pg_url):
    s = Settings(_env_file=None, database={"url": pg_url})
    engine = bootstrap.admin_engine(s, {})
    groups = [("66666666-6666-6666-6666-666666666666", "FIN", "reader", "fin-extra")]
    count = "SELECT (SELECT count(*) FROM ops.departments), (SELECT count(*) FROM ops.access_groups), (SELECT count(*) FROM ops.settings)"
    bootstrap.migrate(engine)
    bootstrap.seed_registry(engine, s, {}, groups)
    with engine.connect() as c:
        first = c.execute(text(count)).one()
    bootstrap.migrate(engine)
    bootstrap.seed_registry(engine, s, {}, groups)
    with engine.connect() as c:
        assert c.execute(text(count)).one() == first
        assert first[2] == len(s.tuning.model_dump()) + len(s.models.model_dump()) and first[1] >= 6


def test_users_locally_only_ensures_the_roles(ctx, pg_url):
    s = Settings(_env_file=None, database={"url": pg_url})
    bootstrap.create_service_users(bootstrap.admin_engine(s, {}), s, {})
    with ctx.ops.engine.connect() as c:
        have = {r[0] for r in c.execute(text("SELECT rolname FROM pg_roles WHERE rolname LIKE 'r\\_%'"))}
    assert set(grants.ROLES) <= have


def test_the_azure_engine_sends_an_entra_token_as_the_password_and_requires_tls(monkeypatch):
    class Cred:
        def get_token(self, scope):
            assert scope == TOKEN_SCOPE == "https://ossrdbms-aad.database.windows.net/.default"
            return type("T", (), {"token": "tok"})()

    db = Database(entra_auth=True, host="pg.example.azure.com", name="docai", user="id-app-chat-api")
    e = entra_engine(db, Cred())
    seen: dict = {}
    monkeypatch.setattr(e.dialect.loaded_dbapi, "connect", lambda *a, **kw: seen.update(kw) or (_ for _ in ()).throw(RuntimeError("stop")))
    with pytest.raises(RuntimeError, match="stop"):
        e.connect()
    assert (seen["password"], seen["sslmode"], seen["host"], seen["user"]) == ("tok", "require", "pg.example.azure.com", "id-app-chat-api")
    assert e.pool._recycle < 1800


def test_users_on_azure_creates_missing_principals_and_grants_the_role():
    executed: list[tuple[str, dict]] = []

    class Result:
        def first(self):
            return None  # no such role yet

    class Conn:
        def execute(self, stmt, params=None):
            executed.append((str(stmt), params or {}))
            return Result()

    class Begin:
        def __enter__(self):
            return Conn()

        def __exit__(self, *a):
            return False

    class Engine:
        def begin(self):
            return Begin()

    s = Settings(_env_file=None, database={"entra_auth": True, "host": "h", "user": "u"})
    bootstrap.create_service_users(Engine(), s, {"OID_app_chat_api": "oid-1"})  # type: ignore[arg-type]
    sql = "\n".join(q for q, _ in executed)
    assert "pgaadauth_create_principal_with_oid(:n, :oid, 'service', false, false)" in sql
    assert ({"n": "id-app-chat-api", "oid": "oid-1"}) in [p for _, p in executed]
    assert 'GRANT r_chat TO "id-app-chat-api"' in sql
    assert "id-job-intake" not in sql, "no object ID in the state: skipped"


def test_users_on_azure_create_the_principal_on_the_directory_engine_and_grant_on_the_main_one():
    """pgaadauth is installed only in the `postgres` database: the function runs there, the GRANT in `docai`."""
    log: list[tuple[str, str]] = []

    def engine(name: str):
        class Result:
            def first(self):
                return None

        class Conn:
            def execute(self, stmt, params=None):
                log.append((name, str(stmt)))
                return Result()

        class Begin:
            def __enter__(self):
                return Conn()

            def __exit__(self, *a):
                return False

        class Engine:
            def begin(self):
                return Begin()

        return Engine()

    s = Settings(_env_file=None, database={"entra_auth": True, "host": "h", "user": "u"})
    bootstrap.create_service_users(engine("docai"), s, {"OID_app_chat_api": "oid-1"}, engine("postgres"))  # type: ignore[arg-type]
    assert [n for n, q in log if "pgaadauth" in q] == ["postgres"]
    assert [n for n, q in log if q.startswith("GRANT r_chat")] == ["docai"]
    assert all(n == "docai" for n, q in log if "pg_roles" in q)
