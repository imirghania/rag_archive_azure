"""Roles for each service identity, their table grants, and row-level security on review tasks (spec, Workflow 4/7).

The statements live in docai.db.grants so that tests/test_db_security.py checks the database against the same list.
Login users for the managed identities are created by the deployment and added to these roles."""
from alembic import op

from docai.db import grants

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for stmt in (*grants.role_statements(), *grants.grant_statements(), *grants.rls_statements()):
        op.execute(stmt)


def downgrade() -> None:
    op.execute(f"DROP POLICY {grants.RLS_POLICY} ON {grants.SCHEMA}.{grants.RLS_TABLE}")
    op.execute(f"ALTER TABLE {grants.SCHEMA}.{grants.RLS_TABLE} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {grants.SCHEMA}.{grants.RLS_TABLE} DISABLE ROW LEVEL SECURITY")
    for role in (*grants.ROLES, grants.EXEMPT_ROLE):  # the roles stay: they are shared by every database on the server
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {grants.SCHEMA} FROM {role}")
        op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA {grants.SCHEMA} FROM {role}")
        op.execute(f"REVOKE ALL ON SCHEMA {grants.SCHEMA} FROM {role}")
