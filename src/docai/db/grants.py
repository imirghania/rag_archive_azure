"""Database roles, table grants and the row-level-security rule, in one place. The security migration (0002_security.py)
applies them and tests/test_db_security.py checks that the database holds exactly these.

Each service identity logs in as a user that is a member of one `r_*` role. The roles are created NOLOGIN; the deployment
adds the login users. The T-SQL version let a role EXECUTE a stored procedure that touched tables the role could not.
The transactions now run as the caller, so every table a procedure touched is granted below, marked "was a procedure"."""
from __future__ import annotations

from .tables import metadata

SCHEMA = "ops"
EXEMPT_ROLE = "rls_exempt"  # members are not filtered by row-level security: the pipeline and the hint worker
EXEMPT_MEMBERS = ("r_pipeline", "r_hint")
ROLES = ("r_pipeline", "r_review", "r_chat", "r_upload", "r_notifier", "r_hint", "r_admin", "r_lookup")

# role -> [(privileges, tables)]. A privilege may name columns: "SELECT (seq, hint_id)".
_GRANTS: dict[str, list[tuple[str, tuple[str, ...]]]] = {
    # Pipeline jobs: the state tables, and what register_dossier, finish_*, create_review_task, apply_decision, ... touched.
    "r_pipeline": [
        ("SELECT, INSERT, UPDATE", ("dossiers", "files", "pages", "documents", "uploads", "upload_files", "upload_dossiers",
                                    "content_flags", "review_tasks")),
        ("SELECT, INSERT, UPDATE, DELETE", ("outbox",)),
        ("SELECT, INSERT, UPDATE, DELETE", ("conversations",)),  # the watchdog purges expired rows
        ("SELECT", ("departments", "access_groups", "settings", "hints", "department_counters")),
        ("SELECT, INSERT", ("decisions_applied",)),  # SELECT: the post-review job folds decisions; INSERT: apply_decision (was a procedure)
        ("INSERT", ("inbox",)),
    ],
    # Review app: review, hints, access, and the outbox relay.
    "r_review": [
        ("SELECT", ("dossiers", "files", "pages", "documents", "departments", "access_groups", "hint_publications", "review_demand",
                    "conversations", "inbox", "upload_dossiers")),
        ("SELECT, UPDATE", ("review_tasks", "hints")),  # review_tasks UPDATE: claim_task, renew_lease, decide_task (was a procedure)
        ("SELECT, INSERT, UPDATE", ("outbox",)),  # INSERT: enqueue and every transaction that queues a message (was a procedure)
        ("SELECT, INSERT, UPDATE", ("department_counters",)),  # claim_task (was a procedure)
        ("SELECT, UPDATE", ("content_flags",)),
        ("UPDATE", ("dossiers",)),  # change_dossier_acl (was a procedure)
        ("SELECT, INSERT", ("acl_audit",)),
        ("INSERT", ("audit",)),
        ("UPDATE", ("inbox",)),
    ],
    # Chat app: write answers and feedback; feed review demand and submit hints (both were the only two procedures it could run).
    "r_chat": [
        ("SELECT, INSERT", ("conversations", "feedback")),
        ("SELECT", ("departments", "access_groups", "dossiers", "documents")),
        ("INSERT", ("review_demand", "hint_scope", "outbox")),  # record_demand, submit_hint (was a procedure)
        ("INSERT", ("hints",)),
        ("SELECT (seq, hint_id)", ("hints",)),  # RETURNING needs it; no read access to the hint content
    ],
    # Upload API.
    "r_upload": [
        ("SELECT, INSERT, UPDATE", ("uploads", "upload_files")),
        ("SELECT", ("departments", "access_groups", "dossiers", "upload_dossiers")),
    ],
    # Notifier and hint worker.
    "r_notifier": [
        ("SELECT, INSERT, UPDATE", ("inbox",)),
        ("SELECT", ("access_groups", "departments")),
    ],
    "r_hint": [
        ("SELECT, UPDATE", ("hints",)),
        ("SELECT", ("dossiers", "documents", "hint_scope", "access_groups", "departments")),
        ("INSERT", ("hint_publications", "outbox")),  # outbox: set_hint_status queues hint.changed (was a procedure)
        ("SELECT, INSERT", ("review_tasks",)),  # create_review_task (was a procedure)
    ],
    # Admin pages: read the status tables and edit the registry. No content: the DENY of the T-SQL version is "not granted" here.
    "r_admin": [
        ("SELECT", tuple(t.name for t in metadata.sorted_tables if t.name not in ("conversations", "hints"))),
        ("INSERT, UPDATE", ("departments", "access_groups", "settings")),
    ],
    # app-retrieval and app-verifier work out the caller's access scope from the token and the group registry, and nothing else.
    "r_lookup": [
        ("SELECT", ("access_groups", "departments")),
    ],
}

# Standalone sequences (identity columns need no grant): role -> sequences it may call nextval on.
SEQUENCE_GRANTS = {"r_pipeline": ("seq_unfiled",), "r_upload": ("seq_upload",)}

# The review app sets app.departments to the departments where the caller is expert or steward ('-' for none).
RLS_TABLE = "review_tasks"
RLS_POLICY = "review_tasks_departments"
_VISIBLE = (f"pg_has_role(current_user, '{EXEMPT_ROLE}', 'member') "
            "OR department = ANY (string_to_array(coalesce(current_setting('app.departments', true), ''), ','))")


def table_privileges() -> dict[tuple[str, str], set[str]]:
    """(role, table) -> table-wide privileges, as `information_schema.role_table_grants` lists them."""
    out: dict[tuple[str, str], set[str]] = {}
    for role, entries in _GRANTS.items():
        for privs, tables in entries:
            if "(" in privs:  # column-level grants are not table privileges
                continue
            for t in tables:
                out.setdefault((role, t), set()).update(p.strip() for p in privs.split(","))
    return out


def grant_statements() -> list[str]:
    stmts = [f"GRANT USAGE ON SCHEMA {SCHEMA} TO {role}" for role in ROLES]
    for role, entries in _GRANTS.items():
        for privs, tables in entries:
            stmts += [f"GRANT {privs} ON {SCHEMA}.{t} TO {role}" for t in tables]
    for role, seqs in SEQUENCE_GRANTS.items():
        stmts += [f"GRANT USAGE ON SEQUENCE {SCHEMA}.{s} TO {role}" for s in seqs]
    stmts += [f"GRANT {EXEMPT_ROLE} TO {m}" for m in EXEMPT_MEMBERS]
    return stmts


def role_statements() -> list[str]:
    """Idempotent: roles are cluster-wide, so a second database on the same server finds them already there."""
    return [f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{r}') THEN CREATE ROLE {r} NOLOGIN; END IF; END $$"
            for r in (*ROLES, EXEMPT_ROLE)]


def rls_statements() -> list[str]:
    t = f"{SCHEMA}.{RLS_TABLE}"
    return [f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY",
            f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY",
            f"CREATE POLICY {RLS_POLICY} ON {t} USING ({_VISIBLE}) WITH CHECK ({_VISIBLE})"]
