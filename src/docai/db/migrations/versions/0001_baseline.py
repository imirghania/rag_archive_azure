"""Baseline: the `ops` schema, generated from docai.db.tables (tables, indexes, constraints), plus the two sequences
that Alembic does not compare. Nothing was deployed before this, so there is no data to carry over."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS ops')
    op.execute('CREATE SEQUENCE ops.seq_unfiled')
    op.execute('CREATE SEQUENCE ops.seq_upload')
    op.create_table('acl_audit',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('dossier_id', sa.String(length=40), nullable=True),
    sa.Column('hint_id', sa.String(length=20), nullable=True),
    sa.Column('changed_by', sa.String(length=200), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('old_acl', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('new_acl', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('widened', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_acl_audit')),
    schema='ops'
    )
    op.create_table('audit',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('actor', sa.String(length=200), nullable=False),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('subject', sa.String(length=200), nullable=True),
    sa.Column('detail', sa.Text(), nullable=True),
    sa.Column('at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit')),
    schema='ops'
    )
    op.create_table('conversations',
    sa.Column('answer_id', sa.String(length=30), nullable=False),
    sa.Column('conversation_id', sa.String(length=40), nullable=False),
    sa.Column('turn_no', sa.Integer(), nullable=False),
    sa.Column('user_oid', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('language', sa.String(length=5), nullable=True),
    sa.Column('intent', sa.String(length=20), nullable=True),
    sa.Column('answer', sa.Text(), nullable=True),
    sa.Column('abstained', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('abstain_reason', sa.String(length=40), nullable=True),
    sa.Column('scope_hash', sa.CHAR(length=64), nullable=True),
    sa.Column('evidence', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('verdict', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('answer_id', name=op.f('pk_conversations')),
    schema='ops'
    )
    op.create_index('ix_conv_age', 'conversations', ['created_at'], unique=False, schema='ops')
    op.create_index('ix_conv_thread', 'conversations', ['conversation_id', 'turn_no'], unique=False, schema='ops')
    op.create_table('decisions_applied',
    sa.Column('task_id', sa.BigInteger(), nullable=False),
    sa.Column('document_id', sa.String(length=60), nullable=False),
    sa.Column('new_version', sa.Integer(), nullable=False),
    sa.Column('applied_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('task_id', name=op.f('pk_decisions_applied')),
    schema='ops'
    )
    op.create_table('departments',
    sa.Column('code', sa.String(length=3), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('default_acl_kind', sa.String(length=12), server_default='reader', nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("default_acl_kind IN ('reader','expert','steward','uploader','restricted')", name='ck_dept_default_kind'),
    sa.PrimaryKeyConstraint('code', name=op.f('pk_departments')),
    schema='ops'
    )
    op.create_table('inbox',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('recipient_kind', sa.String(length=10), nullable=False),
    sa.Column('recipient_value', sa.String(length=100), nullable=True),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.String(length=1000), nullable=True),
    sa.Column('link', sa.String(length=300), nullable=True),
    sa.Column('event_id', sa.String(length=200), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('read_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("recipient_kind IN ('user','steward','admin')", name='ck_inbox_kind'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_inbox')),
    schema='ops'
    )
    op.create_index('ux_inbox_event', 'inbox', ['event_id', 'recipient_kind', 'recipient_value'], unique=True, schema='ops', postgresql_where=sa.text('event_id IS NOT NULL'), postgresql_nulls_not_distinct=True)
    op.create_table('outbox',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('message_id', sa.String(length=300), nullable=False),
    sa.Column('destination', sa.String(length=40), nullable=False),
    sa.Column('session_id', sa.String(length=100), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=8), server_default='pending', nullable=False),
    sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('sent_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("jsonb_typeof(body::jsonb) = 'object'", name='ck_outbox_json'),
    sa.CheckConstraint("status IN ('pending','sent')", name='ck_outbox_status'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_outbox')),
    sa.UniqueConstraint('message_id', 'destination', name='uq_outbox_message'),
    schema='ops'
    )
    op.create_index('ix_outbox_pending', 'outbox', ['status', 'id'], unique=False, schema='ops', postgresql_where=sa.text("status = 'pending'"))
    op.create_table('review_demand',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('line_key', sa.String(length=80), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('answer_id', sa.String(length=30), nullable=True),
    sa.Column('at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('retrieved','blocked')", name='ck_demand_kind'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_review_demand')),
    schema='ops'
    )
    op.create_index('ix_demand_line', 'review_demand', ['line_key', 'at'], unique=False, schema='ops', postgresql_include=['kind'])
    op.create_table('settings',
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_by', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_settings')),
    schema='ops'
    )
    op.create_table('access_groups',
    sa.Column('group_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('department', sa.String(length=3), nullable=False),
    sa.Column('kind', sa.String(length=12), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('reader','expert','steward','uploader','restricted')", name='ck_access_group_kind'),
    sa.ForeignKeyConstraint(['department'], ['ops.departments.code'], name=op.f('fk_access_groups_department_departments')),
    sa.PrimaryKeyConstraint('group_id', name=op.f('pk_access_groups')),
    schema='ops'
    )
    op.create_index('ix_access_groups_dept_kind', 'access_groups', ['department', 'kind'], unique=False, schema='ops')
    op.create_table('content_flags',
    sa.Column('chunk_id', sa.String(length=100), nullable=False),
    sa.Column('document_id', sa.String(length=60), nullable=False),
    sa.Column('department', sa.String(length=3), nullable=False),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=10), server_default='open', nullable=False),
    sa.Column('flagged_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('decided_by', sa.String(length=200), nullable=True),
    sa.Column('decided_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('open','confirmed','cleared')", name='ck_flag_status'),
    sa.ForeignKeyConstraint(['department'], ['ops.departments.code'], name=op.f('fk_content_flags_department_departments')),
    sa.PrimaryKeyConstraint('chunk_id', name=op.f('pk_content_flags')),
    schema='ops'
    )
    op.create_table('department_counters',
    sa.Column('department', sa.String(length=3), nullable=False),
    sa.Column('claims', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.ForeignKeyConstraint(['department'], ['ops.departments.code'], name=op.f('fk_department_counters_department_departments')),
    sa.PrimaryKeyConstraint('department', name=op.f('pk_department_counters')),
    schema='ops'
    )
    op.create_table('dossiers',
    sa.Column('dossier_id', sa.String(length=40), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('department', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='received', nullable=False),
    sa.Column('priority', sa.String(length=8), server_default='online', nullable=False),
    sa.Column('source', sa.String(length=10), server_default='upload', nullable=False),
    sa.Column('reprocess_of', sa.Integer(), nullable=True),
    sa.Column('upload_id', sa.String(length=30), nullable=True),
    sa.Column('segmentation', sa.String(length=10), server_default='auto', nullable=False),
    sa.Column('manifest_path', sa.String(length=400), nullable=False),
    sa.Column('manifest_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('expected_pages', sa.Integer(), nullable=True),
    sa.Column('total_pages', sa.Integer(), nullable=True),
    sa.Column('pages_done', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('pages_failed', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('files_to_prepare', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('segmented', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('documents_total', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('acl_groups', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('acl_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('failure_reason', sa.String(length=200), nullable=True),
    sa.Column('created_by', sa.String(length=200), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("jsonb_typeof(acl_groups) = 'array'", name='ck_dossier_acl_json'),
    sa.CheckConstraint("source IN ('upload','reprocess')", name='ck_dossier_source'),
    sa.CheckConstraint("status IN ('received','preparing','preprocessing','processing','segmenting','indexing','completed','partial','failed','failed_intake','superseded')", name='ck_dossier_status'),
    sa.ForeignKeyConstraint(['department'], ['ops.departments.code'], name=op.f('fk_dossiers_department_departments')),
    sa.PrimaryKeyConstraint('dossier_id', 'revision', name='pk_dossiers'),
    schema='ops'
    )
    op.create_index('ix_dossiers_status', 'dossiers', ['status', 'updated_at'], unique=False, schema='ops', postgresql_include=['department'])
    op.create_index('ux_dossiers_manifest', 'dossiers', ['dossier_id', 'manifest_hash'], unique=True, schema='ops', postgresql_where=sa.text("source = 'upload'"))
    op.create_table('feedback',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('answer_id', sa.String(length=30), nullable=False),
    sa.Column('user_oid', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('rating', sa.SmallInteger(), nullable=False),
    sa.Column('comment', sa.String(length=1000), nullable=True),
    sa.Column('at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('rating IN (-1, 1)', name='ck_feedback_rating'),
    sa.ForeignKeyConstraint(['answer_id'], ['ops.conversations.answer_id'], name=op.f('fk_feedback_answer_id_conversations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feedback')),
    schema='ops'
    )
    op.create_table('hints',
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False, start=731), nullable=False),
    sa.Column('hint_id', sa.String(), sa.Computed("'hint-' || lpad(seq::text, 6, '0')", persisted=True), nullable=False),
    sa.Column('department', sa.String(length=3), nullable=False),
    sa.Column('type', sa.String(length=18), nullable=False),
    sa.Column('status', sa.String(length=18), server_default='submitted', nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('language', sa.String(length=5), server_default='en', nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('terms', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('scope_level', sa.String(length=12), server_default='department', nullable=False),
    sa.Column('scope_dossier_ids', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('evidence', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('evidence_status', sa.String(length=12), server_default='documentary', nullable=False),
    sa.Column('acl_groups', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('check_results', postgresql.JSONB(none_as_null=True, astext_type=sa.Text()), nullable=True),
    sa.Column('from_answer', sa.String(length=30), nullable=True),
    sa.Column('target_line_key', sa.String(length=80), nullable=True),
    sa.Column('suggested_text', sa.Text(), nullable=True),
    sa.Column('author_oid', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('author_name', sa.String(length=200), server_default='', nullable=False),
    sa.Column('editor_name', sa.String(length=200), nullable=True),
    sa.Column('approved_by_oid', sa.UUID(as_uuid=False), nullable=True),
    sa.Column('approved_by_name', sa.String(length=200), nullable=True),
    sa.Column('approved_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('review_by', sa.Date(), nullable=True),
    sa.Column('decision_reason', sa.String(length=500), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("jsonb_typeof(scope_dossier_ids) = 'array' AND jsonb_typeof(evidence) = 'array'", name='ck_hint_json'),
    sa.CheckConstraint("status IN ('submitted','awaiting_approval','approved','rejected','published','revoked')", name='ck_hint_status'),
    sa.CheckConstraint("type IN ('context_note','terminology','transcription_fix')", name='ck_hint_type'),
    sa.ForeignKeyConstraint(['department'], ['ops.departments.code'], name=op.f('fk_hints_department_departments')),
    sa.PrimaryKeyConstraint('seq', name=op.f('pk_hints')),
    schema='ops'
    )
    op.create_index('ix_hints_dept_status', 'hints', ['department', 'status'], unique=False, schema='ops')
    op.create_index('ux_hints_hint_id', 'hints', ['hint_id'], unique=True, schema='ops')
    op.create_table('review_tasks',
    sa.Column('task_id', sa.BigInteger(), sa.Identity(always=False, start=88412), nullable=False),
    sa.Column('department', sa.String(length=3), nullable=False),
    sa.Column('dossier_id', sa.String(length=40), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.String(length=60), nullable=True),
    sa.Column('page_no', sa.Integer(), nullable=False),
    sa.Column('line_id', sa.String(length=12), nullable=False),
    sa.Column('line_key', sa.String(length=80), nullable=False),
    sa.Column('reason', sa.String(length=20), server_default='readers_disagree', nullable=False),
    sa.Column('status', sa.String(length=10), server_default='open', nullable=False),
    sa.Column('suggested_text', sa.Text(), nullable=True),
    sa.Column('hint_id', sa.String(length=20), nullable=True),
    sa.Column('lease_token', sa.UUID(as_uuid=False), nullable=True),
    sa.Column('lease_expires_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('claimed_by', sa.UUID(as_uuid=False), nullable=True),
    sa.Column('claim_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('abandon_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('decision', sa.String(length=14), nullable=True),
    sa.Column('decided_by', sa.UUID(as_uuid=False), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('closed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("reason IN ('readers_disagree','ocr_too_unsure','expert_hint')", name='ck_task_reason'),
    sa.CheckConstraint("status IN ('open','claimed','done','escalated')", name='ck_task_status'),
    sa.ForeignKeyConstraint(['department'], ['ops.departments.code'], name=op.f('fk_review_tasks_department_departments')),
    sa.PrimaryKeyConstraint('task_id', name=op.f('pk_review_tasks')),
    schema='ops'
    )
    op.create_index('ix_review_queue', 'review_tasks', ['department', 'status', 'created_at'], unique=False, schema='ops')
    op.create_index('ux_review_task_line', 'review_tasks', ['line_key'], unique=True, schema='ops', postgresql_where=sa.text("status IN ('open','claimed','escalated')"))
    op.create_table('uploads',
    sa.Column('upload_id', sa.String(length=30), nullable=False),
    sa.Column('department', sa.String(length=3), nullable=False),
    sa.Column('mode', sa.String(length=8), nullable=False),
    sa.Column('dossier_id', sa.String(length=40), nullable=True),
    sa.Column('status', sa.String(length=12), server_default='open', nullable=False),
    sa.Column('reject_reason', sa.String(length=40), nullable=True),
    sa.Column('uploaded_by_oid', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('uploaded_by_name', sa.String(length=200), server_default='', nullable=False),
    sa.Column('manifest_hash', sa.CHAR(length=64), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=True),
    sa.Column('intake_sent', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('scan_attempt', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_activity_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('committed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("mode IN ('dossier','bulk')", name='ck_upload_mode'),
    sa.CheckConstraint("status IN ('open','scanning','committed','rejected','expired')", name='ck_upload_status'),
    sa.ForeignKeyConstraint(['department'], ['ops.departments.code'], name=op.f('fk_uploads_department_departments')),
    sa.PrimaryKeyConstraint('upload_id', name=op.f('pk_uploads')),
    schema='ops'
    )
    op.create_table('documents',
    sa.Column('document_id', sa.String(length=60), nullable=False),
    sa.Column('dossier_id', sa.String(length=40), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('first_page', sa.Integer(), nullable=False),
    sa.Column('last_page', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=12), server_default='segmented', nullable=False),
    sa.Column('current_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('indexed_version', sa.Integer(), nullable=True),
    sa.Column('has_gaps', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=True),
    sa.Column('doc_type', sa.String(length=100), nullable=True),
    sa.Column('doc_date', sa.Date(), nullable=True),
    sa.Column('reference', sa.String(length=200), nullable=True),
    sa.Column('subject', sa.String(length=500), nullable=True),
    sa.Column('languages', sa.String(length=50), nullable=True),
    sa.Column('min_trust', sa.String(length=30), nullable=True),
    sa.Column('cabinet', sa.String(length=10), nullable=True),
    sa.Column('shelf', sa.String(length=10), nullable=True),
    sa.Column('section', sa.String(length=10), nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('segmented','described','chunked','indexed','removed')", name='ck_document_status'),
    sa.ForeignKeyConstraint(['dossier_id', 'revision'], ['ops.dossiers.dossier_id', 'ops.dossiers.revision'], name='fk_documents_dossier'),
    sa.PrimaryKeyConstraint('document_id', name=op.f('pk_documents')),
    sa.UniqueConstraint('dossier_id', 'revision', 'seq', name='uq_document_seq'),
    schema='ops'
    )
    op.create_table('files',
    sa.Column('dossier_id', sa.String(length=40), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=260), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=8), nullable=False),
    sa.Column('route', sa.String(length=8), nullable=False),
    sa.Column('status', sa.String(length=12), server_default='registered', nullable=False),
    sa.Column('location', sa.String(length=10), server_default='raw', nullable=False),
    sa.Column('bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.CHAR(length=64), nullable=False),
    sa.Column('pages', sa.Integer(), nullable=True),
    sa.Column('converted_to', sa.String(length=400), nullable=True),
    sa.Column('failure_reason', sa.String(length=200), nullable=True),
    sa.CheckConstraint("route IN ('scan','digital')", name='ck_file_route'),
    sa.CheckConstraint("status IN ('registered','converting','ready','failed')", name='ck_file_status'),
    sa.ForeignKeyConstraint(['dossier_id', 'revision'], ['ops.dossiers.dossier_id', 'ops.dossiers.revision'], name='fk_files_dossier'),
    sa.PrimaryKeyConstraint('dossier_id', 'revision', 'name', name='pk_files'),
    schema='ops'
    )
    op.create_table('hint_publications',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('hint_seq', sa.BigInteger(), nullable=False),
    sa.Column('hint_version', sa.Integer(), nullable=False),
    sa.Column('destination', sa.String(length=20), nullable=False),
    sa.Column('action', sa.String(length=10), nullable=False),
    sa.Column('reason', sa.String(length=30), server_default='approval', nullable=False),
    sa.Column('at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['hint_seq'], ['ops.hints.seq'], name=op.f('fk_hint_publications_hint_seq_hints')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_hint_publications')),
    schema='ops'
    )
    op.create_table('hint_scope',
    sa.Column('seq', sa.BigInteger(), nullable=False),
    sa.Column('dossier_id', sa.String(length=40), nullable=False),
    sa.ForeignKeyConstraint(['seq'], ['ops.hints.seq'], name=op.f('fk_hint_scope_seq_hints')),
    sa.PrimaryKeyConstraint('seq', 'dossier_id', name='pk_hint_scope'),
    schema='ops'
    )
    op.create_index('ix_hint_scope_dossier', 'hint_scope', ['dossier_id'], unique=False, schema='ops')
    op.create_table('pages',
    sa.Column('dossier_id', sa.String(length=40), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('page_no', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=24), server_default='preprocessed', nullable=False),
    sa.Column('source_file', sa.String(length=260), nullable=False),
    sa.Column('frame', sa.Integer(), nullable=False),
    sa.Column('text_layer', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('flagged_lines', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('resend_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('failure_reason', sa.String(length=200), nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('preprocessed','ocr_done','awaiting_second_read','reconciled','failed')", name='ck_page_status'),
    sa.ForeignKeyConstraint(['dossier_id', 'revision'], ['ops.dossiers.dossier_id', 'ops.dossiers.revision'], name='fk_pages_dossier'),
    sa.PrimaryKeyConstraint('dossier_id', 'revision', 'page_no', name='pk_pages'),
    schema='ops'
    )
    op.create_index('ix_pages_stuck', 'pages', ['status', 'updated_at'], unique=False, schema='ops', postgresql_where=sa.text("status IN ('preprocessed','ocr_done','awaiting_second_read')"))
    op.create_table('upload_dossiers',
    sa.Column('upload_id', sa.String(length=30), nullable=False),
    sa.Column('dossier_id', sa.String(length=40), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('manifest_hash', sa.CHAR(length=64), nullable=False),
    sa.Column('intake_sent', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['upload_id'], ['ops.uploads.upload_id'], name=op.f('fk_upload_dossiers_upload_id_uploads')),
    sa.PrimaryKeyConstraint('upload_id', 'dossier_id', name='pk_upload_dossiers'),
    schema='ops'
    )
    op.create_table('upload_files',
    sa.Column('upload_id', sa.String(length=30), nullable=False),
    sa.Column('name', sa.String(length=260), nullable=False),
    sa.Column('bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.CHAR(length=64), nullable=False),
    sa.Column('blocks_total', sa.Integer(), nullable=False),
    sa.Column('blocks_received', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.ForeignKeyConstraint(['upload_id'], ['ops.uploads.upload_id'], name=op.f('fk_upload_files_upload_id_uploads')),
    sa.PrimaryKeyConstraint('upload_id', 'name', name='pk_upload_files'),
    schema='ops'
    )


def downgrade() -> None:
    op.drop_table('upload_files', schema='ops')
    op.drop_table('upload_dossiers', schema='ops')
    op.drop_index('ix_pages_stuck', table_name='pages', schema='ops', postgresql_where=sa.text("status IN ('preprocessed','ocr_done','awaiting_second_read')"))
    op.drop_table('pages', schema='ops')
    op.drop_index('ix_hint_scope_dossier', table_name='hint_scope', schema='ops')
    op.drop_table('hint_scope', schema='ops')
    op.drop_table('hint_publications', schema='ops')
    op.drop_table('files', schema='ops')
    op.drop_table('documents', schema='ops')
    op.drop_table('uploads', schema='ops')
    op.drop_index('ux_review_task_line', table_name='review_tasks', schema='ops', postgresql_where=sa.text("status IN ('open','claimed','escalated')"))
    op.drop_index('ix_review_queue', table_name='review_tasks', schema='ops')
    op.drop_table('review_tasks', schema='ops')
    op.drop_index('ux_hints_hint_id', table_name='hints', schema='ops')
    op.drop_index('ix_hints_dept_status', table_name='hints', schema='ops')
    op.drop_table('hints', schema='ops')
    op.drop_table('feedback', schema='ops')
    op.drop_index('ux_dossiers_manifest', table_name='dossiers', schema='ops', postgresql_where=sa.text("source = 'upload'"))
    op.drop_index('ix_dossiers_status', table_name='dossiers', schema='ops', postgresql_include=['department'])
    op.drop_table('dossiers', schema='ops')
    op.drop_table('department_counters', schema='ops')
    op.drop_table('content_flags', schema='ops')
    op.drop_index('ix_access_groups_dept_kind', table_name='access_groups', schema='ops')
    op.drop_table('access_groups', schema='ops')
    op.drop_table('settings', schema='ops')
    op.drop_index('ix_demand_line', table_name='review_demand', schema='ops', postgresql_include=['kind'])
    op.drop_table('review_demand', schema='ops')
    op.drop_index('ix_outbox_pending', table_name='outbox', schema='ops', postgresql_where=sa.text("status = 'pending'"))
    op.drop_table('outbox', schema='ops')
    op.drop_index('ux_inbox_event', table_name='inbox', schema='ops', postgresql_where=sa.text('event_id IS NOT NULL'), postgresql_nulls_not_distinct=True)
    op.drop_table('inbox', schema='ops')
    op.drop_table('departments', schema='ops')
    op.drop_table('decisions_applied', schema='ops')
    op.drop_index('ix_conv_thread', table_name='conversations', schema='ops')
    op.drop_index('ix_conv_age', table_name='conversations', schema='ops')
    op.drop_table('conversations', schema='ops')
    op.drop_table('audit', schema='ops')
    op.drop_table('acl_audit', schema='ops')
    op.execute('DROP SEQUENCE ops.seq_upload')
    op.execute('DROP SEQUENCE ops.seq_unfiled')
    op.execute('DROP SCHEMA ops')
