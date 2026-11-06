"""The `ops` schema as SQLAlchemy Core tables. Alembic compares this metadata with the migrations (`alembic check`).

State of the pipeline, review, hints, answers and access (spec: State lives in PostgreSQL). Timestamps are
`timestamptz`, written in UTC. The atomic state changes that used to be T-SQL procedures are Python transactions in
`docai.adapters.sql.ops`."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    Sequence,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, TIMESTAMP, UUID

SCHEMA = "ops"
metadata = MetaData(
    schema=SCHEMA,
    naming_convention={
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
    },
)

TS = TIMESTAMP(timezone=True)
GUID = UUID(as_uuid=False)  # str in Python, lower case
NOW = text("now()")
OPEN_TASK = text("status IN ('open','claimed','escalated')")


def _t(name: str, *items, **kw) -> Table:
    return Table(name, metadata, *items, **kw)


def created(name: str = "created_at", nullable: bool = False) -> Column:
    return Column(name, TS, nullable=nullable, server_default=None if nullable else NOW)


def _json(name: str, *, default: str | None = None, nullable: bool = True) -> Column:
    return Column(name, JSONB(none_as_null=True), nullable=nullable, server_default=text(f"'{default}'::jsonb") if default else None)


# Sequences for generated IDs (spec, Workflow 9). Alembic does not compare standalone sequences; the baseline creates them.
seq_unfiled = Sequence("seq_unfiled", schema=SCHEMA, metadata=metadata)
seq_upload = Sequence("seq_upload", schema=SCHEMA, metadata=metadata)

# registry and settings
departments = _t(
    "departments",
    Column("code", String(3), primary_key=True),
    Column("name", String(100), nullable=False),
    Column("default_acl_kind", String(12), nullable=False, server_default="reader"),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    created(),
    CheckConstraint("default_acl_kind IN ('reader','expert','steward','uploader','restricted')", name="ck_dept_default_kind"),
)
# Every group that may appear in an acl_groups list must have a row here, or it is ignored when the access scope is
# computed from a token (spec, Workflow 7: the treasury group).
access_groups = _t(
    "access_groups",
    Column("group_id", GUID, primary_key=True),
    Column("department", String(3), ForeignKey("ops.departments.code"), nullable=False),
    Column("kind", String(12), nullable=False),
    Column("name", String(200), nullable=False),
    created(),
    CheckConstraint("kind IN ('reader','expert','steward','uploader','restricted')", name="ck_access_group_kind"),
    Index("ix_access_groups_dept_kind", "department", "kind"),
)
settings = _t(
    "settings",
    Column("key", String(100), primary_key=True),
    Column("value", Text, nullable=False),
    created("updated_at"),
    Column("updated_by", String(200)),
)

# uploads
uploads = _t(
    "uploads",
    Column("upload_id", String(30), primary_key=True),  # up-20261104-0042
    Column("department", String(3), ForeignKey("ops.departments.code"), nullable=False),
    Column("mode", String(8), nullable=False),
    Column("dossier_id", String(40)),
    Column("status", String(12), nullable=False, server_default="open"),
    Column("reject_reason", String(40)),
    Column("uploaded_by_oid", GUID, nullable=False),
    Column("uploaded_by_name", String(200), nullable=False, server_default=""),
    Column("manifest_hash", CHAR(64)),
    Column("revision", Integer),
    Column("intake_sent", Boolean, nullable=False, server_default=text("false")),  # the commit retry sends intake exactly once
    Column("scan_attempt", Integer, nullable=False, server_default=text("0")),
    created(),
    created("last_activity_at"),
    created("committed_at", nullable=True),
    CheckConstraint("mode IN ('dossier','bulk')", name="ck_upload_mode"),
    CheckConstraint("status IN ('open','scanning','committed','rejected','expired')", name="ck_upload_status"),
)
upload_files = _t(
    "upload_files",
    Column("upload_id", String(30), ForeignKey("ops.uploads.upload_id"), nullable=False),
    Column("name", String(260), nullable=False),
    Column("bytes", BigInteger, nullable=False),
    Column("sha256", CHAR(64), nullable=False),
    Column("blocks_total", Integer, nullable=False),
    Column("blocks_received", Integer, nullable=False, server_default=text("0")),
    PrimaryKeyConstraint("upload_id", "name", name="pk_upload_files"),
)
upload_dossiers = _t(  # an upload that becomes several dossiers (bulk mode)
    "upload_dossiers",
    Column("upload_id", String(30), ForeignKey("ops.uploads.upload_id"), nullable=False),
    Column("dossier_id", String(40), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("manifest_hash", CHAR(64), nullable=False),
    Column("intake_sent", Boolean, nullable=False, server_default=text("false")),  # dossier.received is sent exactly once per dossier
    PrimaryKeyConstraint("upload_id", "dossier_id", name="pk_upload_dossiers"),
)

# dossiers, files, pages, documents
dossiers = _t(
    "dossiers",
    Column("dossier_id", String(40), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("department", String(3), ForeignKey("ops.departments.code"), nullable=False),
    Column("status", String(16), nullable=False, server_default="received"),
    Column("priority", String(8), nullable=False, server_default="online"),
    Column("source", String(10), nullable=False, server_default="upload"),
    Column("reprocess_of", Integer),  # the revision whose files are processed again
    Column("upload_id", String(30)),
    Column("segmentation", String(10), nullable=False, server_default="auto"),
    Column("manifest_path", String(400), nullable=False),
    Column("manifest_hash", CHAR(64), nullable=False),
    Column("expected_pages", Integer),
    Column("total_pages", Integer),  # final before the first page message is sent
    Column("pages_done", Integer, nullable=False, server_default=text("0")),
    Column("pages_failed", Integer, nullable=False, server_default=text("0")),
    Column("files_to_prepare", Integer, nullable=False, server_default=text("0")),
    Column("segmented", Boolean, nullable=False, server_default=text("false")),
    Column("documents_total", Integer, nullable=False, server_default=text("0")),
    _json("acl_groups", default="[]", nullable=False),  # JSON array of group IDs
    Column("acl_version", Integer, nullable=False, server_default=text("1")),
    Column("failure_reason", String(200)),
    Column("created_by", String(200)),
    created(),
    created("updated_at"),
    created("completed_at", nullable=True),
    PrimaryKeyConstraint("dossier_id", "revision", name="pk_dossiers"),
    CheckConstraint(
        "status IN ('received','preparing','preprocessing','processing','segmenting','indexing','completed','partial','failed',"
        "'failed_intake','superseded')", name="ck_dossier_status"),
    CheckConstraint("source IN ('upload','reprocess')", name="ck_dossier_source"),
    CheckConstraint("jsonb_typeof(acl_groups) = 'array'", name="ck_dossier_acl_json"),
    # a reprocess reuses the hash on purpose
    Index("ux_dossiers_manifest", "dossier_id", "manifest_hash", unique=True, postgresql_where=text("source = 'upload'")),
    Index("ix_dossiers_status", "status", "updated_at", postgresql_include=["department"]),
)
files = _t(
    "files",
    Column("dossier_id", String(40), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("name", String(260), nullable=False),
    Column("seq", Integer, nullable=False),  # manifest order
    Column("type", String(8), nullable=False),
    Column("route", String(8), nullable=False),
    Column("status", String(12), nullable=False, server_default="registered"),
    Column("location", String(10), nullable=False, server_default="raw"),
    Column("bytes", BigInteger, nullable=False),
    Column("sha256", CHAR(64), nullable=False),
    Column("pages", Integer),
    Column("converted_to", String(400)),
    Column("failure_reason", String(200)),
    PrimaryKeyConstraint("dossier_id", "revision", "name", name="pk_files"),
    ForeignKeyConstraint(["dossier_id", "revision"], ["ops.dossiers.dossier_id", "ops.dossiers.revision"], name="fk_files_dossier"),
    CheckConstraint("route IN ('scan','digital')", name="ck_file_route"),
    CheckConstraint("status IN ('registered','converting','ready','failed')", name="ck_file_status"),
)
pages = _t(
    "pages",
    Column("dossier_id", String(40), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("page_no", Integer, nullable=False),
    Column("status", String(24), nullable=False, server_default="preprocessed"),
    Column("source_file", String(260), nullable=False),
    Column("frame", Integer, nullable=False),
    Column("text_layer", Boolean, nullable=False, server_default=text("false")),
    Column("flagged_lines", Integer, nullable=False, server_default=text("0")),
    Column("resend_count", Integer, nullable=False, server_default=text("0")),
    Column("failure_reason", String(200)),
    created("updated_at"),
    created("finished_at", nullable=True),
    PrimaryKeyConstraint("dossier_id", "revision", "page_no", name="pk_pages"),
    ForeignKeyConstraint(["dossier_id", "revision"], ["ops.dossiers.dossier_id", "ops.dossiers.revision"], name="fk_pages_dossier"),
    CheckConstraint("status IN ('preprocessed','ocr_done','awaiting_second_read','reconciled','failed')", name="ck_page_status"),
    Index("ix_pages_stuck", "status", "updated_at", postgresql_where=text("status IN ('preprocessed','ocr_done','awaiting_second_read')")),
)
documents = _t(
    "documents",
    Column("document_id", String(60), primary_key=True),
    Column("dossier_id", String(40), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("seq", Integer, nullable=False),
    Column("first_page", Integer, nullable=False),
    Column("last_page", Integer, nullable=False),
    Column("status", String(12), nullable=False, server_default="segmented"),
    Column("current_version", Integer, nullable=False, server_default=text("1")),
    Column("indexed_version", Integer),
    Column("has_gaps", Boolean, nullable=False, server_default=text("false")),
    Column("title", String(300)),
    Column("doc_type", String(100)),
    Column("doc_date", Date),
    Column("reference", String(200)),
    Column("subject", String(500)),
    Column("languages", String(50)),
    Column("min_trust", String(30)),
    Column("cabinet", String(10)),
    Column("shelf", String(10)),
    Column("section", String(10)),
    created("updated_at"),
    ForeignKeyConstraint(["dossier_id", "revision"], ["ops.dossiers.dossier_id", "ops.dossiers.revision"], name="fk_documents_dossier"),
    UniqueConstraint("dossier_id", "revision", "seq", name="uq_document_seq"),
    CheckConstraint("status IN ('segmented','described','chunked','indexed','removed')", name="ck_document_status"),
)

# review
review_tasks = _t(
    "review_tasks",
    Column("task_id", BigInteger, Identity(start=88412), primary_key=True),
    Column("department", String(3), ForeignKey("ops.departments.code"), nullable=False),
    Column("dossier_id", String(40), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("document_id", String(60)),  # known after segmentation
    Column("page_no", Integer, nullable=False),
    Column("line_id", String(12), nullable=False),
    Column("line_key", String(80), nullable=False),
    Column("reason", String(20), nullable=False, server_default="readers_disagree"),
    Column("status", String(10), nullable=False, server_default="open"),
    Column("suggested_text", Text),  # pre-filled for an expert hint
    Column("hint_id", String(20)),
    Column("lease_token", GUID),
    Column("lease_expires_at", TS),
    Column("claimed_by", GUID),
    Column("claim_count", Integer, nullable=False, server_default=text("0")),
    Column("abandon_count", Integer, nullable=False, server_default=text("0")),
    Column("decision", String(14)),
    Column("decided_by", GUID),
    created(),
    created("closed_at", nullable=True),
    CheckConstraint("reason IN ('readers_disagree','ocr_too_unsure','expert_hint')", name="ck_task_reason"),
    CheckConstraint("status IN ('open','claimed','done','escalated')", name="ck_task_status"),
    Index("ux_review_task_line", "line_key", unique=True, postgresql_where=OPEN_TASK),
    Index("ix_review_queue", "department", "status", "created_at"),
)
review_demand = _t(
    "review_demand",
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("line_key", String(80), nullable=False),
    Column("kind", String(10), nullable=False),
    Column("answer_id", String(30)),
    created("at"),
    CheckConstraint("kind IN ('retrieved','blocked')", name="ck_demand_kind"),
    Index("ix_demand_line", "line_key", "at", postgresql_include=["kind"]),
)
decisions_applied = _t(
    "decisions_applied",
    Column("task_id", BigInteger, primary_key=True),  # a redelivered decision stops here
    Column("document_id", String(60), nullable=False),
    Column("new_version", Integer, nullable=False),
    created("applied_at"),
)
department_counters = _t(
    "department_counters",
    Column("department", String(3), ForeignKey("ops.departments.code"), primary_key=True),
    Column("claims", BigInteger, nullable=False, server_default=text("0")),  # every Nth claim takes the oldest task
)
content_flags = _t(
    "content_flags",
    Column("chunk_id", String(100), primary_key=True),
    Column("document_id", String(60), nullable=False),
    Column("department", String(3), ForeignKey("ops.departments.code"), nullable=False),
    Column("source", String(30), nullable=False),
    Column("status", String(10), nullable=False, server_default="open"),
    created("flagged_at"),
    Column("decided_by", String(200)),
    created("decided_at", nullable=True),
    CheckConstraint("status IN ('open','confirmed','cleared')", name="ck_flag_status"),
)

# hints
hints = _t(
    "hints",
    Column("seq", BigInteger, Identity(start=731), primary_key=True),
    Column("hint_id", String, Computed("'hint-' || lpad(seq::text, 6, '0')", persisted=True), nullable=False),
    Column("department", String(3), ForeignKey("ops.departments.code"), nullable=False),
    Column("type", String(18), nullable=False),
    Column("status", String(18), nullable=False, server_default="submitted"),
    Column("version", Integer, nullable=False, server_default=text("1")),  # raised when a steward edits the wording
    Column("row_version", Integer, nullable=False, server_default=text("1")),  # raised by every change; stale messages are dropped
    Column("language", String(5), nullable=False, server_default="en"),
    Column("text", Text, nullable=False),
    _json("terms"),  # JSON array, terminology hints
    Column("scope_level", String(12), nullable=False, server_default="department"),
    _json("scope_dossier_ids", default="[]", nullable=False),
    _json("evidence", default="[]", nullable=False),  # [{chunk_id, lines, quote, selected_by, suggested}]
    Column("evidence_status", String(12), nullable=False, server_default="documentary"),
    _json("acl_groups"),  # computed at publish as the intersection
    _json("check_results"),
    Column("from_answer", String(30)),
    Column("target_line_key", String(80)),  # transcription_fix
    Column("suggested_text", Text),
    Column("author_oid", GUID, nullable=False),
    Column("author_name", String(200), nullable=False, server_default=""),
    Column("editor_name", String(200)),
    Column("approved_by_oid", GUID),
    Column("approved_by_name", String(200)),
    Column("approved_at", TS),
    Column("review_by", Date),
    Column("decision_reason", String(500)),
    created(),
    created("updated_at"),
    CheckConstraint("type IN ('context_note','terminology','transcription_fix')", name="ck_hint_type"),
    CheckConstraint("status IN ('submitted','awaiting_approval','approved','rejected','published','revoked')", name="ck_hint_status"),
    CheckConstraint("jsonb_typeof(scope_dossier_ids) = 'array' AND jsonb_typeof(evidence) = 'array'", name="ck_hint_json"),
    Index("ux_hints_hint_id", "hint_id", unique=True),
    Index("ix_hints_dept_status", "department", "status"),
)
hint_scope = _t(
    "hint_scope",
    Column("seq", BigInteger, ForeignKey("ops.hints.seq"), nullable=False),
    Column("dossier_id", String(40), nullable=False),
    PrimaryKeyConstraint("seq", "dossier_id", name="pk_hint_scope"),
    Index("ix_hint_scope_dossier", "dossier_id"),
)
hint_publications = _t(
    "hint_publications",
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("hint_seq", BigInteger, ForeignKey("ops.hints.seq"), nullable=False),
    Column("hint_version", Integer, nullable=False),
    Column("destination", String(20), nullable=False),  # notes_index | synonyms_en | synonyms_ar | glossary
    Column("action", String(10), nullable=False),  # upsert | delete | acl_update
    Column("reason", String(30), nullable=False, server_default="approval"),  # approval | acl_change | revoke
    created("at"),
)

# answers, feedback, inbox
conversations = _t(
    "conversations",
    Column("answer_id", String(30), primary_key=True),  # ans-7c41
    Column("conversation_id", String(40), nullable=False),
    Column("turn_no", Integer, nullable=False),
    Column("user_oid", GUID, nullable=False),
    Column("question", Text, nullable=False),
    Column("language", String(5)),
    Column("intent", String(20)),
    Column("answer", Text),
    Column("abstained", Boolean, nullable=False, server_default=text("false")),
    Column("abstain_reason", String(40)),
    Column("scope_hash", CHAR(64)),
    _json("evidence"),  # JSON: chunks returned to the run
    _json("verdict"),
    Column("latency_ms", Integer),
    created(),
    Index("ix_conv_thread", "conversation_id", "turn_no"),
    Index("ix_conv_age", "created_at"),
)
feedback = _t(
    "feedback",
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("answer_id", String(30), ForeignKey("ops.conversations.answer_id", ondelete="CASCADE"), nullable=False),
    Column("user_oid", GUID, nullable=False),
    Column("rating", SmallInteger, nullable=False),
    Column("comment", String(1000)),
    created("at"),
    CheckConstraint("rating IN (-1, 1)", name="ck_feedback_rating"),
)
inbox = _t(
    "inbox",
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("recipient_kind", String(10), nullable=False),
    Column("recipient_value", String(100)),  # user oid, or department code for stewards
    Column("type", String(40), nullable=False),
    Column("title", String(200), nullable=False),
    Column("body", String(1000)),
    Column("link", String(300)),
    Column("event_id", String(200)),  # notifier de-duplicates on this
    created(),
    created("read_at", nullable=True),
    CheckConstraint("recipient_kind IN ('user','steward','admin')", name="ck_inbox_kind"),
    # an admin row has no recipient_value: NULLs count as equal, so the same event is not stored twice for it
    Index("ux_inbox_event", "event_id", "recipient_kind", "recipient_value", unique=True,
        postgresql_where=text("event_id IS NOT NULL"), postgresql_nulls_not_distinct=True),
)

# outbox and audit
outbox = _t(
    "outbox",
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("message_id", String(300), nullable=False),
    Column("destination", String(40), nullable=False),  # queue or topic name
    Column("session_id", String(100)),
    Column("body", Text, nullable=False),  # the envelope as it is sent: kept as text, so it reaches the queue byte for byte
    Column("status", String(8), nullable=False, server_default="pending"),
    Column("attempts", Integer, nullable=False, server_default=text("0")),
    created(),
    created("sent_at", nullable=True),
    CheckConstraint("status IN ('pending','sent')", name="ck_outbox_status"),
    CheckConstraint("jsonb_typeof(body::jsonb) = 'object'", name="ck_outbox_json"),
    UniqueConstraint("message_id", "destination", name="uq_outbox_message"),
    Index("ix_outbox_pending", "status", "id", postgresql_where=text("status = 'pending'")),
)
acl_audit = _t(
    "acl_audit",
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("dossier_id", String(40)),
    Column("hint_id", String(20)),
    Column("changed_by", String(200), nullable=False),
    Column("reason", String(500), nullable=False),
    _json("old_acl"),
    _json("new_acl"),
    Column("widened", Boolean, nullable=False, server_default=text("false")),
    created("at"),
)
audit = _t(
    "audit",
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("actor", String(200), nullable=False),
    Column("action", String(60), nullable=False),
    Column("subject", String(200)),
    Column("detail", Text),
    created("at"),
)
