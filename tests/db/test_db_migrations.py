"""The schema as Alembic builds it: from an empty database, in step with docai.db.tables, and with the grants of docai.db.grants."""
import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from conftest import alembic_config
from docai.core import catalog
from docai.db import grants, tables


@pytest.fixture
def empty_db(pg_url):
    """A new empty database on the test server (roles are shared by the whole server, so migrating twice finds them already there)."""
    name = f"docai_mig_{uuid.uuid4().hex[:8]}"
    admin = create_engine(pg_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f"CREATE DATABASE {name}"))
    try:
        yield make_url(pg_url).set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE {name} WITH (FORCE)"))
        admin.dispose()


def test_alembic_upgrade_on_an_empty_database_matches_the_table_definitions_and_can_be_undone(empty_db):
    cfg = alembic_config(empty_db)
    command.upgrade(cfg, "head")
    command.check(cfg)  # raises when tables.py and the migrations disagree: write a migration for the change
    e = create_engine(empty_db)
    with e.connect() as c:
        names = {r[0] for r in c.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'ops'"))}
        assert names == {t.name for t in tables.metadata.sorted_tables}
        assert c.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0002"
    command.downgrade(cfg, "base")
    with e.connect() as c:
        assert c.execute(text("SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'ops'")).scalar() == 0
    command.upgrade(cfg, "head")  # and again: the roles from the first run are reused
    e.dispose()


def test_the_database_holds_exactly_the_grants_of_the_constants_and_the_roles_are_not_login_roles(pg_url):
    e = create_engine(pg_url)
    with e.connect() as c:
        have: dict[tuple[str, str], set[str]] = {}
        for role, table, priv in c.execute(text("SELECT grantee, table_name, privilege_type FROM information_schema.role_table_grants "
                                                 "WHERE table_schema = 'ops' AND grantee = ANY(:roles)"), {"roles": list(grants.ROLES)}):
            have.setdefault((role, table), set()).add(priv)
        assert have == grants.table_privileges()
        login = c.execute(text("SELECT rolname FROM pg_roles WHERE rolname = ANY(:r) AND rolcanlogin"), {"r": [*grants.ROLES, grants.EXEMPT_ROLE]}).all()
        assert login == []
        exempt = {r[0] for r in c.execute(text("SELECT m.rolname FROM pg_auth_members a JOIN pg_roles m ON m.oid = a.member "
                                                "JOIN pg_roles g ON g.oid = a.roleid WHERE g.rolname = :g"), {"g": grants.EXEMPT_ROLE})}
        assert exempt == set(grants.EXEMPT_MEMBERS)
        rls = c.execute(text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = 'ops.review_tasks'::regclass")).one()
        assert tuple(rls) == (True, True)
    e.dispose()


def test_every_service_identity_in_the_catalog_has_a_role_the_migration_creates():
    assert {c.sql_role for c in catalog.COMPONENTS if c.sql_role} <= set(grants.ROLES)


def test_a_role_cannot_read_what_it_was_not_granted(ctx, as_role):
    from sqlalchemy.exc import ProgrammingError
    chat = as_role("r_chat")
    chat.record_demand([{"line_key": "k", "kind": "blocked"}])
    chat.save_turn(answer_id="ans-1", conversation_id="c-1", user_oid="aaaaaaaa-0000-0000-0000-000000000001", question="q", answer="a", abstained=False,
                   abstain_reason=None, intent=None, language="en", evidence=[], verdict=None, scope_hash="0" * 64, latency_ms=1)
    hid = chat.submit_hint(department="FIN", type="context_note", language="en", text="x", author_oid="aaaaaaaa-0000-0000-0000-000000000001")
    assert hid == "hint-000731"
    with pytest.raises(ProgrammingError):
        chat.get_hint(hid)  # the chat app may write a hint and never read hints
    admin = as_role("r_admin")
    assert admin.list_dossiers() == []
    with pytest.raises(ProgrammingError):
        admin.history("c-1", "aaaaaaaa-0000-0000-0000-000000000001")  # the admin pages see no conversation content
    admin.add_department("XX", "Registry edit")
    assert as_role("r_lookup").registered_groups()
    with pytest.raises(ProgrammingError):
        as_role("r_lookup").list_dossiers()


def test_the_pipeline_hint_notifier_and_upload_roles_can_run_their_own_calls(ctx, as_role):
    files = [{"name": "a.tif", "seq": 1, "type": "tiff", "route": "scan", "bytes": 1, "sha256": "a" * 64, "pages": 1}]
    kw = dict(dossier_id="FIN-X-1", department="FIN", manifest_path="m", manifest_hash="b" * 64, files=files)
    pipe = as_role("r_pipeline")
    assert pipe.register_dossier(**kw).status == "registered"
    assert pipe.register_pages("FIN-X-1", 1, [{"page_no": 1, "source_file": "a.tif", "frame": 1}]) == (1, 0)
    tid = pipe.create_review_task(department="FIN", dossier_id="FIN-X-1", revision=1, page_no=1, line_id="L1", line_key="FIN-X-1@r1/p001/L1")
    assert tid == 88412
    assert pipe.register_documents("FIN-X-1", 1, [{"document_id": "D1", "seq": 1, "first_page": 1, "last_page": 1}]) == 1
    assert pipe.get_task(tid)["document_id"] == "D1"
    assert pipe.apply_decision(tid, "D1") == (2, False) and pipe.mark_indexed("D1", 2)
    assert pipe.finish_page("FIN-X-1", 1, 1, "reconciled") == (1, 1) and pipe.try_complete_dossier("FIN-X-1", 1) == "completed"
    assert pipe.next_unfiled_seq() == 1
    pipe.upsert_content_flag("c1", "D1", "FIN", "scan")
    pipe.enqueue("m1", "q-index", '{"a": 1}')
    up = as_role("r_upload")
    uid = up.create_upload(department="FIN", mode="dossier", dossier_id=None, uploaded_by_oid="aaaaaaaa-0000-0000-0000-000000000001", uploaded_by_name="s",
                           files=[{"name": "a.tif", "bytes": 5, "sha256": "c" * 64}], block_bytes=4)
    assert up.get_upload(uid)["files"][0]["blocks_total"] == 2 and up.latest_revision("FIN-X-1") == 1
    hid = ctx.ops.submit_hint(department="FIN", type="transcription_fix", language="en", text="t", author_oid="aaaaaaaa-0000-0000-0000-000000000001")
    hint = as_role("r_hint")
    assert hint.set_hint_status(hid, "rejected", 1, actor_oid="aaaaaaaa-0000-0000-0000-000000000002", actor_name="r") == 2
    hint.record_publication(hid, "notes_index", "delete", "revoke")
    assert hint.create_review_task(department="FIN", dossier_id="FIN-X-1", revision=1, page_no=1, line_id="L2", line_key="FIN-X-1@r1/p001/L2") == tid + 1
    note = as_role("r_notifier")
    assert note.add_inbox(recipient_kind="admin", recipient_value=None, type="t", title="x", event_id="e1")
    assert not note.add_inbox(recipient_kind="admin", recipient_value=None, type="t", title="x", event_id="e1"), "the same event is stored once, even with no recipient"
    assert len(note.inbox_for("u", [], True)) == 1
