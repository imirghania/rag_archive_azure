"""PostgreSQL adapter of the OpsStore port, on SQLAlchemy Core (psycopg 3). One implementation for local runs, tests and Azure.

Every state change that must be atomic or count exactly once is one transaction function here (they were T-SQL procedures):
idempotent inserts use ON CONFLICT DO NOTHING, claims use FOR UPDATE SKIP LOCKED, and outbox rows are written in the same
transaction as the change that needs them. The schema is `docai.db.tables`, applied by Alembic."""
from __future__ import annotations

import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import Date as SaDate
from sqlalchemy import (
    Engine,
    and_,
    case,
    cast,
    delete,
    func,
    insert,
    literal,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

from docai.contracts.messages import Envelope
from docai.db import tables as T
from docai.db.engine import engine_for
from docai.ports import DocumentRow, Dossier, FileRow, LeaseLost, OutboxRow, PageRow, RegisterResult

FINAL_PAGE = ("reconciled", "failed")
OPEN_TASK = ("open", "claimed", "escalated")


def _plain(v: Any) -> Any:
    """Timestamps as ISO strings, dates as strings, UUIDs as lower-case strings: the shapes the callers always got."""
    if isinstance(v, datetime):
        return v.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


def _row(r: Any) -> dict[str, Any]:
    return {k: _plain(v) for k, v in r._mapping.items()}


def _uuid(v: str) -> str | None:
    try:
        return str(uuid.UUID(str(v)))
    except ValueError:
        return None


class SqlOps:
    """`clock` is a hook for tests: when it is set every timestamp the store writes comes from it, otherwise from the database clock.
    `set_departments` is remembered per thread and sent at the start of every transaction (row-level security reads it)."""

    def __init__(self, url: str, clock=None, engine: Engine | None = None) -> None:
        self.url, self.clock, self.engine, self._local = url, clock, engine or engine_for(url), threading.local()

    # plumbing
    @contextmanager
    def _tx(self):
        with self.engine.begin() as c:
            deps = getattr(self._local, "departments", None)
            if deps is not None:  # transaction-local, so a pooled connection never carries it to the next caller
                c.execute(select(func.set_config("app.departments", deps, True)))
            yield c

    def _now(self):
        """A value for a timestamp column or comparison: the test clock's datetime, or the database's now()."""
        return self.clock.now() if self.clock else func.now()

    def _stamp(self, col: str) -> dict[str, Any]:
        return {col: self.clock.now()} if self.clock else {}  # an absent column takes its default: now()

    def _pynow(self) -> datetime:
        return self.clock.now() if self.clock else datetime.now(UTC)

    def _all(self, stmt) -> list[dict[str, Any]]:
        with self._tx() as c:
            return [_row(r) for r in c.execute(stmt)]

    def _one(self, stmt) -> dict[str, Any] | None:
        rows = self._all(stmt)
        return rows[0] if rows else None

    def _exec(self, stmt) -> int:
        with self._tx() as c:
            return c.execute(stmt).rowcount

    def _exec_returning(self, stmt) -> Any:
        with self._tx() as c:
            return c.execute(stmt).scalar()

    def reset_for_tests(self) -> None:
        """Empties every table and restarts the counters. Only the test suite calls this."""
        names = ", ".join(f"{T.SCHEMA}.{t.name}" for t in T.metadata.sorted_tables)
        with self.engine.begin() as c:
            c.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))  # identity columns restart at their seeds
            for s in (T.seq_unfiled, T.seq_upload):
                c.execute(text(f"ALTER SEQUENCE {T.SCHEMA}.{s.name} RESTART WITH 1"))
        self._local.departments = None

    # registry
    def add_department(self, code, name) -> None:
        self._exec(pg_insert(T.departments).values(code=code, name=name).on_conflict_do_nothing())

    def add_access_group(self, group_id, department, kind, name) -> None:
        self._exec(pg_insert(T.access_groups).values(group_id=group_id, department=department, kind=kind, name=name).on_conflict_do_nothing())

    def registered_groups(self) -> dict[str, tuple[str, str]]:
        g = T.access_groups
        return {r["group_id"].lower(): (r["department"], r["kind"]) for r in self._all(select(g.c.group_id, g.c.department, g.c.kind))}

    # intake
    def register_dossier(self, *, dossier_id, department, manifest_path, manifest_hash, files, source="upload", from_revision=None,
                        upload_id=None, segmentation="auto", expected_pages=None) -> RegisterResult:
        d = T.dossiers
        with self._tx() as c:
            c.execute(select(func.pg_advisory_xact_lock(func.hashtext(dossier_id))))  # revisions of one dossier are numbered one at a time
            latest = c.execute(select(func.max(d.c.revision)).where(d.c.dossier_id == dossier_id)).scalar()
            if source == "upload":
                dup = c.execute(select(d.c.revision).where(d.c.dossier_id == dossier_id, d.c.manifest_hash == manifest_hash, d.c.source == "upload")).scalar()
                if dup is not None:
                    return RegisterResult("duplicate", dup)
            if source == "reprocess" and (latest is None or latest != from_revision):
                return RegisterResult("stale", latest or 0)
            rev = (latest or 0) + 1
            # A later revision inherits the dossier's current access; a first revision takes the department default.
            prev = c.execute(select(d.c.acl_groups, d.c.acl_version).where(d.c.dossier_id == dossier_id).order_by(d.c.revision.desc()).limit(1)).first()
            if prev:
                acl, aclv = list(prev.acl_groups), prev.acl_version
            else:
                g, dep = T.access_groups, T.departments
                acl = [r.group_id for r in c.execute(
                    select(g.c.group_id).select_from(g.join(dep, and_(dep.c.code == g.c.department, g.c.kind == dep.c.default_acl_kind)))
                    .where(g.c.department == department).order_by(g.c.name, g.c.group_id))]
                aclv = 1
            prepare = sum(1 for f in files if f["route"] == "digital")
            c.execute(insert(d).values(
                dossier_id=dossier_id, revision=rev, department=department, status="preparing" if prepare else "received", source=source,
                reprocess_of=from_revision, upload_id=upload_id, segmentation=segmentation, manifest_path=manifest_path, manifest_hash=manifest_hash,
                expected_pages=expected_pages, files_to_prepare=prepare, acl_groups=acl, acl_version=aclv))
            if files:
                c.execute(insert(T.files), [
                    {"dossier_id": dossier_id, "revision": rev, "name": f["name"], "seq": f["seq"], "type": f["type"], "route": f["route"],
                    "status": "registered" if f["route"] == "digital" else "ready", "bytes": f["bytes"], "sha256": f["sha256"], "pages": f.get("pages")}
                    for f in files])
            return RegisterResult("registered", rev, prepare, [x.lower() for x in acl])

    def get_dossier(self, dossier_id, revision) -> Dossier:
        r = self._one(select(T.dossiers).where(T.dossiers.c.dossier_id == dossier_id, T.dossiers.c.revision == revision))
        if not r:
            raise KeyError(f"{dossier_id}@r{revision}")
        return Dossier(r["dossier_id"], r["revision"], r["department"], r["status"], 
                    r["priority"], r["total_pages"], r["pages_done"], r["pages_failed"],
                    r["files_to_prepare"], bool(r["segmented"]), r["documents_total"], 
                    [g.lower() for g in r["acl_groups"]], r["acl_version"],
                    r["manifest_hash"].strip(), r["manifest_path"], r["segmentation"])

    def list_files(self, dossier_id, revision) -> list[FileRow]:
        f = T.files
        return [FileRow(r["name"], r["seq"], r["type"], r["route"], r["status"], 
                        r["location"], r["pages"], (r["sha256"] or "").strip())
                for r in self._all(select(f).where(
                    f.c.dossier_id == dossier_id, f.c.revision == revision
                    ).order_by(f.c.seq))]

    def finish_file(self, dossier_id, revision, name, status, *, 
                    pages=None, converted_to=None, reason=None):
        """A converted file is counted once. Returns the files still to prepare, or None if it was counted before."""
        if status not in ("ready", "failed"):
            raise ValueError("finish_file: status must be ready or failed")
        f, d = T.files, T.dossiers
        with self._tx() as c:
            vals: dict[str, Any] = {"status": status, "pages": func.coalesce(pages, f.c.pages), "converted_to": converted_to, "failure_reason": reason}
            if status == "ready" and converted_to is not None:
                vals["location"] = "extracted"
            hit = c.execute(update(f).where(f.c.dossier_id == dossier_id, f.c.revision == revision, f.c.name == name,
                                            f.c.status.in_(("registered", "converting"))).values(**vals))
            if hit.rowcount != 1:
                return None
            return c.execute(update(d).where(
                d.c.dossier_id == dossier_id, d.c.revision == revision
                ).values(
                    files_to_prepare=d.c.files_to_prepare - 1, 
                    updated_at=self._now(),
                    status=case((d.c.files_to_prepare - 1 == 0, "preprocessing"), 
                    else_=d.c.status)
                    ).returning(d.c.files_to_prepare)).scalar()

    def set_dossier_status(self, dossier_id, revision, status, reason=None) -> None:
        d = T.dossiers
        self._exec(update(d).where(
            d.c.dossier_id == dossier_id, 
            d.c.revision == revision
            ).values(
                status=status, 
                failure_reason=func.coalesce(reason, d.c.failure_reason), 
                updated_at=self._now()
                ))

    # pages
    def register_pages(self, dossier_id, revision, pages):
        """All page rows and total_pages in one transaction, before the first page message is sent. None on a repeat."""
        d, p = T.dossiers, T.pages
        with self._tx() as c:
            total = c.execute(
                select(d.c.total_pages).where(
                    d.c.dossier_id == dossier_id, 
                    d.c.revision == revision
                    ).with_for_update()
                ).first()
            if total is None:
                raise KeyError(f"{dossier_id}@r{revision}")
            if total[0] is not None:
                return None  # idempotent: a retry finds the pages already written
            now = self._pynow()
            if pages:
                c.execute(insert(p), 
                        [{
                        "dossier_id": dossier_id, 
                        "revision": revision, 
                        "page_no": x["page_no"], 
                        "status": "failed" if x.get("failed") else "preprocessed",
                        "source_file": x["source_file"], 
                        "frame": x["frame"], 
                        "text_layer": bool(x.get("text_layer")), 
                        "failure_reason": x.get("reason"),
                        "finished_at": now if x.get("failed") else None, 
                        "updated_at": now
                        } for x in pages
                        ])
            failed = sum(1 for x in pages if x.get("failed"))
            c.execute(update(d).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision == revision
                ).values(
                    total_pages=len(pages), 
                    pages_failed=failed, 
                    status="processing", 
                    updated_at=self._now()
                    ))
            return len(pages), failed

    @staticmethod
    def _page(r) -> PageRow:
        return PageRow(r["page_no"], r["status"], r["source_file"], 
                    r["frame"], bool(r["text_layer"]), r["flagged_lines"])

    def get_page(self, dossier_id, revision, page_no) -> PageRow:
        p = T.pages
        r = self._one(select(p).where(
            p.c.dossier_id == dossier_id, 
            p.c.revision == revision, 
            p.c.page_no == page_no))
        if not r:
            raise KeyError(f"{dossier_id}@r{revision}/p{page_no}")
        return self._page(r)

    def list_pages(self, dossier_id, revision) -> list[PageRow]:
        p = T.pages
        return [self._page(r) for r in self._all(select(p).where(
            p.c.dossier_id == dossier_id, 
            p.c.revision == revision
            ).order_by(p.c.page_no))]

    def set_page_status(self, dossier_id, revision, page_no, status, *, flagged_lines=None) -> None:
        p = T.pages
        self._exec(update(p).where(
            p.c.dossier_id == dossier_id, 
            p.c.revision == revision, 
            p.c.page_no == page_no, 
            p.c.status.not_in(FINAL_PAGE)
            ).values(
                status=status, 
                flagged_lines=func.coalesce(flagged_lines, p.c.flagged_lines), 
                updated_at=self._now()
                )
            )

    def finish_page(self, dossier_id, revision, page_no, new_status, reason=None):
        """Fan-in counter (spec, Mechanics). Returns (finished, total_pages) only when THIS call changed the page."""
        if new_status not in FINAL_PAGE:
            raise ValueError("finish_page: status must be reconciled or failed")
        p, d = T.pages, T.dossiers
        with self._tx() as c:
            hit = c.execute(update(p).where(
                p.c.dossier_id == dossier_id, 
                p.c.revision == revision, 
                p.c.page_no == page_no, 
                p.c.status.not_in(FINAL_PAGE)
                )
                            .values(status=new_status, finished_at=self._now(), updated_at=self._now(), failure_reason=reason))
            if hit.rowcount != 1:
                return None
            r = c.execute(update(d).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision == revision
                ).values(
                    pages_done=d.c.pages_done + (1 if new_status == "reconciled" else 0),
                    pages_failed=d.c.pages_failed + (1 if new_status == "failed" else 0), 
                    updated_at=self._now()
                    ).returning(
                        d.c.pages_done + d.c.pages_failed, d.c.total_pages)
                    ).first()
            return r[0], r[1]

    # review tasks and documents
    def create_review_task(self, *, department, dossier_id, revision, page_no, line_id, line_key, reason="readers_disagree", suggested_text=None, hint_id=None) -> int:
        """One open task per line. Review tasks are created before segmentation, so documents are linked when segmentation registers them."""
        t, docs = T.review_tasks, T.documents
        with self._tx() as c:
            def existing():
                return c.execute(select(t.c.task_id).where(t.c.line_key == line_key, t.c.status.in_(OPEN_TASK))).scalar()
            found = existing()  # looked up first: a conflicting insert would still use up an identity value
            if found is not None:
                return found
            doc = c.execute(select(docs.c.document_id).where(
                docs.c.dossier_id == dossier_id, 
                docs.c.revision == revision,
                docs.c.first_page <= page_no, docs.c.last_page >= page_no
                )).scalar()
            new = c.execute(pg_insert(t).values(
                department=department, dossier_id=dossier_id, 
                revision=revision, document_id=doc, page_no=page_no,
                line_id=line_id, line_key=line_key, reason=reason, 
                suggested_text=suggested_text, hint_id=hint_id
                ).on_conflict_do_nothing(
                    index_elements=[t.c.line_key], 
                    index_where=t.c.status.in_(OPEN_TASK)
                    ).returning(t.c.task_id)).scalar()
            return new if new is not None else existing()  # lost a race with another writer

    def list_tasks(self, department=None, status=None) -> list[dict[str, Any]]:
        t = T.review_tasks
        q = select(t).order_by(t.c.task_id)
        for col, v in ((t.c.department, department), (t.c.status, status)):
            if v:
                q = q.where(col == v)
        return self._all(q)

    def get_task(self, task_id) -> dict[str, Any]:
        r = self._one(select(T.review_tasks).where(
            T.review_tasks.c.task_id == task_id
            ))
        if not r:
            raise KeyError(task_id)
        return r

    def register_documents(self, dossier_id, revision, documents) -> int:
        """Writes the documents of a revision once and links the revision's review tasks to them. Returns the count, or 0 on a repeat."""
        d, docs, t = T.dossiers, T.documents, T.review_tasks
        with self._tx() as c:
            seg = c.execute(select(d.c.segmented).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision == revision
                ).with_for_update()).first()
            if seg is None:
                raise KeyError(f"{dossier_id}@r{revision}")
            if seg[0]:
                return 0
            if documents:
                c.execute(insert(docs), 
                        [{
                            "document_id": x["document_id"], 
                            "dossier_id": dossier_id, 
                            "revision": revision, 
                            "seq": x["seq"],
                            "first_page": x["first_page"], 
                            "last_page": x["last_page"], 
                            "title": x.get("title"),
                            "has_gaps": bool(x.get("has_gaps"))
                        } 
                        for x in documents
                        ])
            c.execute(update(t).where(
                t.c.dossier_id == dossier_id, 
                t.c.revision == revision, 
                docs.c.dossier_id == t.c.dossier_id,
                docs.c.revision == t.c.revision, 
                t.c.page_no >= docs.c.first_page, 
                t.c.page_no <= docs.c.last_page
                ).values(
                    document_id=docs.c.document_id
                    )
                )
            c.execute(update(d).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision == revision
                ).values(
                    segmented=True, 
                    documents_total=len(documents), 
                    status="indexing", 
                    updated_at=self._now()
                    )
                )
            return len(documents)

    @staticmethod
    def _doc(r) -> DocumentRow:
        return DocumentRow(r["document_id"], r["dossier_id"], 
                        r["revision"], r["seq"], r["first_page"], 
                        r["last_page"], r["status"], r["current_version"], 
                        r["indexed_version"], bool(r["has_gaps"]), r["title"])

    def list_documents(self, dossier_id, revision) -> list[DocumentRow]:
        d = T.documents
        return [self._doc(r) 
                for r in self._all(
                    select(d).where(
                        d.c.dossier_id == dossier_id, 
                        d.c.revision == revision
                        ).order_by(d.c.seq)
                    )]

    def get_document(self, document_id) -> DocumentRow:
        r = self._one(select(T.documents).where(
            T.documents.c.document_id == document_id))
        if not r:
            raise KeyError(document_id)
        return self._doc(r)

    def set_document_metadata(self, document_id, meta) -> None:
        d = T.documents
        try:
            doc_date = date.fromisoformat(str(meta.get("doc_date"))[:10])
        except ValueError:
            doc_date = None  # an unreadable date is stored as no date
        self._exec(update(d).where(
            d.c.document_id == document_id, 
            d.c.status.in_(("segmented", "described"))
            ).values(
                status="described", 
                doc_type=meta.get("doc_type"), 
                doc_date=doc_date, 
                reference=meta.get("reference"), 
                subject=meta.get("subject"),
                languages=",".join(meta.get("languages", [])), 
                min_trust=meta.get("min_trust"), 
                updated_at=self._now()
                )
            )

    def mark_indexed(self, document_id, version) -> bool:
        d = T.documents
        return self._exec(update(d).where(
            d.c.document_id == document_id, 
            d.c.current_version >= version, 
            func.coalesce(d.c.indexed_version, 0) < version
            ).values(
                indexed_version=version, 
                status="indexed", 
                updated_at=self._now()
                )
            ) == 1

    def try_complete_dossier(self, dossier_id, revision) -> str:
        """Idempotent. completed when everything is indexed; partial when pages or files failed; failed when no page was readable."""
        d, docs, f = T.dossiers, T.documents, T.files
        with self._tx() as c:
            r = c.execute(select(d).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision == revision
                ).with_for_update()).first()
            if r is None:
                raise KeyError(f"{dossier_id}@r{revision}")
            if (r.status in ("completed", "partial", "failed", "failed_intake", "superseded") or 
                not r.segmented or 
                r.total_pages is None or 
                r.pages_done + r.pages_failed < r.total_pages):
                return r.status
            indexed = c.execute(select(func.count()).select_from(docs).where(
                docs.c.dossier_id == dossier_id, 
                docs.c.revision == revision,
                docs.c.indexed_version.is_not(None))).scalar()
            if indexed < r.documents_total:
                return r.status
            bad = c.execute(select(func.count()).select_from(f).where(
                f.c.dossier_id == dossier_id, 
                f.c.revision == revision, 
                f.c.status == "failed")).scalar()
            status = ("failed" if r.pages_failed == r.total_pages 
                            else ("partial" if r.pages_failed or bad 
                                            else "completed"))
            c.execute(update(d).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision == revision
                ).values(
                    status=status, 
                    completed_at=self._now(), 
                    updated_at=self._now()
                    )
                )
            return status

    def dossier_acl(self, dossier_id) -> list[str]:
        d = T.dossiers
        r = self._one(select(d.c.acl_groups).where(
            d.c.dossier_id == dossier_id
            ).order_by(d.c.revision.desc()).limit(1))
        return [g.lower() for g in r["acl_groups"]] if r else []

    def list_dossiers(self, status=None, department=None, 
                    limit=100) -> list[dict[str, Any]]:
        d = T.dossiers
        q = select(d.c.dossier_id, d.c.revision, d.c.department, 
                d.c.status, d.c.total_pages, d.c.pages_done, d.c.pages_failed, 
                d.c.documents_total, d.c.failure_reason).order_by(
                    d.c.created_at.desc(), 
                    d.c.dossier_id.desc(), 
                    d.c.revision.desc()).limit(limit)
        for col, v in ((d.c.status, status), (d.c.department, department)):
            if v:
                q = q.where(col == v)
        return self._all(q)

    # review
    def set_departments(self, departments) -> None:
        # Sent as transaction-local `app.departments` at the start of every transaction. No department has the code "-", so an empty
        # list shows no task at all (row-level security fails closed).
        self._local.departments = ",".join(departments) or "-"

    def claim_task(self, user_oid, departments, *, 
                lease_minutes=15, escalate_after=3, 
                oldest_every=5, window_days=30, from_status="open"):
        """Demand drives the order (blocked = 10, retrieved = 1, over the last N days); every Nth claim takes the oldest task."""
        if from_status not in ("open", "escalated"):
            raise ValueError("claim_task: from_status must be open or escalated")
        depts = sorted({x.strip() for x in departments if x.strip()})
        if not depts:
            return None
        t, dc, rd, h = T.review_tasks, T.department_counters, T.review_demand, T.hints
        with self._tx() as c:
            now = self._now()
            # A lapsed lease is an abandoned claim; the Nth abandon escalates the task to the stewards.
            escalate = (case((t.c.abandon_count + 1 >= escalate_after, "escalated"), else_="open") 
                        if from_status == "open" 
                        else "open")
            c.execute(update(t).where(
                t.c.status == "claimed", 
                t.c.lease_expires_at < now, t.c.department.in_(depts)
                ).values(
                    abandon_count=t.c.abandon_count + 1, 
                    claimed_by=None, 
                    lease_token=None, 
                    lease_expires_at=None, 
                    status=escalate))
            claims = c.execute(select(func.coalesce(
                func.sum(dc.c.claims), 0)).where(
                    dc.c.department.in_(depts))).scalar()
            take_oldest = claims % oldest_every == oldest_every - 1  # every Nth claim ignores demand so quiet tasks still get done
            demand = (select(rd.c.line_key, 
                            func.sum(
                                case((rd.c.kind == "blocked", 10), else_=1)
                                ).label("score")).where(
                                    rd.c.at >= now - timedelta(days=window_days)
                                    ).group_by(rd.c.line_key).subquery())
            order = ([t.c.created_at, t.c.task_id] 
                    if take_oldest 
                    else [func.coalesce(demand.c.score, 0).desc(), t.c.created_at, t.c.task_id]
                    )
            picked = c.execute(
                select(t.c.task_id).select_from(
                    t.outerjoin(demand, demand.c.line_key == t.c.line_key).outerjoin(
                        h, h.c.hint_id == t.c.hint_id
                        )).where(
                            t.c.status == from_status, 
                            t.c.department.in_(depts),
                            or_(h.c.author_oid.is_(None), h.c.author_oid != user_oid)
                            )  # nobody settles the task of their own hint
                            .order_by(*order).limit(1).with_for_update(
                                skip_locked=True, of=t
                                )
                            ).scalar()
            if picked is None:
                return None
            row = c.execute(update(t).where(
                t.c.task_id == picked
                ).values(
                    status="claimed", 
                    claimed_by=user_oid, 
                    lease_token=str(uuid.uuid4()), 
                    claim_count=t.c.claim_count + 1,
                    lease_expires_at=now + timedelta(minutes=lease_minutes)
                    ).returning(*t.c)).one()
            c.execute(pg_insert(dc).values(
                department=row.department, 
                claims=1).on_conflict_do_update(
                    index_elements=[dc.c.department],
                    set_={"claims": dc.c.claims + 1}
                    )
                )
            out = _row(row)
            out["lease_expires_at"] = row.lease_expires_at
            return out

    def renew_lease(self, task_id, lease_token, lease_minutes=15):
        t = T.review_tasks
        token = _uuid(lease_token)
        if token is None:
            return None
        with self._tx() as c:
            return c.execute(update(t).where(
                t.c.task_id == task_id, 
                t.c.lease_token == token, 
                t.c.status == "claimed"
                ).values(
                    lease_expires_at=self._now() + timedelta(minutes=lease_minutes)).returning(
                        t.c.lease_expires_at
                        )
                    ).scalar()

    def decide_task(self, task_id, lease_token, decision, decided_by, payload) -> str:
        """Closes the task only if the lease token still matches, and queues review.decided in the same transaction."""
        t = T.review_tasks
        token = _uuid(lease_token)
        with self._tx() as c:
            r = None if token is None else c.execute(
                update(t).where(
                    t.c.task_id == task_id, 
                    t.c.lease_token == token, 
                    t.c.status == "claimed"
                    ).values(
                        status="done", 
                        decision=decision, 
                        decided_by=decided_by, 
                        closed_at=self._now(), 
                        lease_token=None, 
                        lease_expires_at=None
                    ).returning(
                        t.c.document_id, 
                        t.c.department, 
                        t.c.dossier_id, 
                        t.c.revision, 
                        t.c.line_key)
                    ).first()
            if r is None:
                raise LeaseLost(f"task {task_id}")
            env = Envelope(type="review.decided", subject=r.line_key, 
                        dossier_id=r.dossier_id, revision=r.revision, 
                        department=r.department, payload=payload)
            self._enqueue(c, f"{r.line_key}:decided:{task_id}", 
                        "q-post-review", env.to_json(), r.document_id)
            return r.document_id

    def apply_decision(self, task_id, document_id):
        """job-post-review: the document version rises once per task; a redelivery gets the stored version back."""
        docs, applied = T.documents, T.decisions_applied
        with self._tx() as c:
            if c.execute(select(docs.c.document_id).where(
                docs.c.document_id == document_id
                ).with_for_update()).first() is None:  # serialises the task's redeliveries
                raise KeyError(document_id)
            old = c.execute(select(applied.c.new_version).where(
                applied.c.task_id == task_id)).scalar()
            if old is not None:
                return old, True
            v = c.execute(update(docs).where(
                docs.c.document_id == document_id
                ).values(
                    current_version=docs.c.current_version + 1, 
                    updated_at=self._now()
                    ).returning(docs.c.current_version)).scalar()
            c.execute(insert(applied).values(
                task_id=task_id, 
                document_id=document_id, 
                new_version=v))
            return v, False

    def applied_tasks(self, document_id) -> dict[int, int]:
        a = T.decisions_applied
        return {
            r["task_id"]: r["new_version"] 
            for r in self._all(
            select(a.c.task_id, a.c.new_version).where(
                a.c.document_id == document_id)
            )
            }

    def record_demand(self, hits, answer_id=None) -> None:
        if hits:
            with self._tx() as c:  # plain SQL for the same reason as _enqueue: r_chat may INSERT here but not SELECT
                c.execute(
                    text(f"INSERT INTO ops.review_demand (line_key, kind, answer_id{', at' if self.clock else ''}) "
                            f"VALUES (:k, :t, :a{', :at' if self.clock else ''})"),
                        [{
                            "k": x["line_key"], 
                            "t": x["kind"], 
                            "a": answer_id, 
                            **({"at": self.clock.now()} if self.clock else {})
                            } for x in hits
                        ])

    def supersede_older_revisions(self, dossier_id, revision) -> list[str]:
        """When a newer revision is `completed`, older revisions are superseded and their documents removed from search (spec, Workflow 8)."""
        d, docs = T.dossiers, T.documents
        with self._tx() as c:
            if c.execute(select(d.c.revision).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision == revision, 
                d.c.status == "completed")).first() is None:
                return []
            c.execute(update(d).where(
                d.c.dossier_id == dossier_id, 
                d.c.revision < revision, 
                d.c.status != "superseded"
                ).values(
                    status="superseded", 
                    updated_at=self._now()
                    ))
            return [r[0] for r in c.execute(update(docs).where(
                docs.c.dossier_id == dossier_id, 
                docs.c.revision < revision, 
                docs.c.status != "removed"
                ).values(
                    status="removed", 
                    updated_at=self._now()
                    ).returning(docs.c.document_id))
                    ]

    # outbox
    @staticmethod
    def _enqueue(c, message_id, destination, body, session_id=None) -> bool:
        # Plain SQL, not insert(): that would add "RETURNING id", which needs SELECT, and r_chat and r_hint may only INSERT here.
        return c.execute(
            text("INSERT INTO ops.outbox (message_id, destination, session_id, body) VALUES (:m, :d, :s, :b) ON CONFLICT DO NOTHING"), {
                "m": message_id, 
                "d": destination, 
                "s": session_id, 
                "b": body
                }
            ).rowcount == 1

    def enqueue(self, message_id, destination, body, session_id=None) -> bool:
        with self._tx() as c:
            return self._enqueue(c, message_id, destination, body, session_id)

    def pending_outbox(self, limit=100) -> list[OutboxRow]:
        o = T.outbox
        return [OutboxRow(r["id"], r["message_id"], r["destination"], 
                        r["session_id"], r["body"])
                for r in self._all(select(o).where(
                    o.c.status == "pending"
                    ).order_by(o.c.id).limit(limit))]

    def mark_outbox_sent(self, row_id) -> None:
        self._exec(update(T.outbox).where(
            T.outbox.c.id == row_id
            ).values(
                status="sent", 
                sent_at=self._now())
            )

    # access, flags, conversations 
    def change_dossier_acl(self, dossier_id, new_acl, changed_by, reason, widened=False) -> int:
        """Changes the groups of every revision, audits it and queues the index and hint updates, atomically."""
        d, docs = T.dossiers, T.documents
        with self._tx() as c:
            cur = c.execute(select(d.c.acl_groups, 
                                d.c.acl_version, 
                                d.c.department).where(
                                    d.c.dossier_id == dossier_id
                                    ).order_by(
                                        d.c.revision.desc()
                                        ).limit(1).with_for_update()).first()
            if cur is None:
                raise KeyError(dossier_id)
            v = cur.acl_version + 1
            c.execute(update(d).where(
                d.c.dossier_id == dossier_id
                ).values(
                    acl_groups=list(new_acl), 
                    acl_version=v, 
                    updated_at=self._now()))
            c.execute(insert(T.acl_audit).values
                    (dossier_id=dossier_id, 
                    changed_by=changed_by, 
                    reason=reason, 
                    old_acl=cur.acl_groups,
                    new_acl=list(new_acl), 
                    widened=widened))
            for doc_id, rev in c.execute(select(docs.c.document_id, 
                                                docs.c.revision).where(
                                                    docs.c.dossier_id == dossier_id, 
                                                    docs.c.status != "removed"
                                                    ).order_by(
                                                        docs.c.revision, 
                                                        docs.c.seq)
                                                    ).all():
                env = Envelope(type="document.acl.changed", 
                            subject=doc_id, dossier_id=dossier_id, 
                            revision=rev, department=cur.department,
                            payload={"acl_version": v})
                self._enqueue(c, f"acl:{doc_id}:acl{v}", "q-index", env.to_json(), doc_id)
            env = Envelope(type="dossier.acl.changed", 
                        subject=dossier_id, dossier_id=dossier_id, 
                        department=cur.department, payload={"acl_version": v})
            self._enqueue(c, f"acl:{dossier_id}:hints:acl{v}", "q-hint-events", env.to_json())
            return v

    def upsert_content_flag(self, chunk_id, document_id, department, source) -> None:
        self._exec(pg_insert(T.content_flags).values(
            chunk_id=chunk_id, 
            document_id=document_id, 
            department=department, 
            source=source
            ).on_conflict_do_nothing()
                )

    def save_turn(self, *, answer_id, conversation_id,
                user_oid, question, answer, abstained, 
                abstain_reason, intent, language, evidence, 
                verdict, scope_hash, latency_ms) -> int:
        cv = T.conversations
        with self._tx() as c:
            c.execute(select(func.pg_advisory_xact_lock(func.hashtext(conversation_id))))  # two answers of a thread are numbered one at a time
            n = c.execute(select(func.coalesce(
                func.max(cv.c.turn_no), 0) + 1).where(
                    cv.c.conversation_id == conversation_id
                    )).scalar()
            c.execute(insert(cv).values(
                answer_id=answer_id, 
                conversation_id=conversation_id, 
                turn_no=n, user_oid=user_oid, 
                question=question, language=language,
                intent=intent, answer=answer, abstained=abstained, 
                abstain_reason=abstain_reason, scope_hash=scope_hash,
                evidence=evidence, verdict=verdict, latency_ms=latency_ms, 
                **self._stamp("created_at")
                ))
            return n

    def history(self, conversation_id, user_oid, limit=3) -> list[dict[str, Any]]:
        cv = T.conversations
        rows = self._all(select(cv).where(
            cv.c.conversation_id == conversation_id, 
            cv.c.user_oid == user_oid
            ).order_by(
                cv.c.turn_no.desc()
                ).limit(limit))
        return list(reversed(rows))

    def purge_conversations(self, older_than_days) -> int:
        return self._exec(delete(T.conversations).where(
            T.conversations.c.created_at < self._now() - timedelta(days=older_than_days)
            ))

    def add_feedback(self, answer_id, user_oid, rating, comment=None) -> None:
        if rating not in (-1, 1):
            raise ValueError("rating is -1 or 1")
        with self._tx() as c:
            if c.execute(select(T.conversations.c.answer_id).where(
                T.conversations.c.answer_id == answer_id
                )).first() is None:
                raise KeyError(answer_id)
            c.execute(insert(T.feedback).values(
                answer_id=answer_id, 
                user_oid=user_oid, 
                rating=rating, 
                comment=comment, 
                **self._stamp("at")
                ))

    # hints
    _MOVES = {
        ("submitted", "awaiting_approval"), 
        ("awaiting_approval", "approved"), 
        ("awaiting_approval", "rejected"),
        ("approved", "published"), 
        ("approved", "revoked"), 
        ("published", "revoked")
        }

    def _hint_message(self, c, hint_id: str, dept: str, 
                    status: str, version: int, row_version: int) -> None:
        env = Envelope(type="hint.changed", 
                    subject=hint_id, department=dept, 
                    payload={
                        "status": status, 
                        "version": version, 
                        "row_version": row_version
                        }
                    )
        self._enqueue(c, f"hint:{hint_id}:v{version}:{status}", 
                    "q-hint-events", env.to_json())

    def submit_hint(self, *, department, type, language, text, 
                    author_oid, author_name="", terms=None, scope_level="department", 
                    scope_dossier_ids=None, evidence=None, evidence_status="documentary", 
                    from_answer=None, target_line_key=None, suggested_text=None) -> str:
        """Writes the hint and its outbox row in one transaction. Returns the hint ID."""
        h = T.hints
        with self._tx() as c:
            seq, hid = c.execute(insert(h).values(
                department=department, type=type, 
                language=language, text=text, terms=terms or None, 
                scope_level=scope_level,
                scope_dossier_ids=list(scope_dossier_ids or []), 
                evidence=list(evidence or []), evidence_status=evidence_status, 
                from_answer=from_answer, target_line_key=target_line_key, 
                suggested_text=suggested_text, author_oid=author_oid, author_name=author_name,
                **self._stamp("created_at"), **self._stamp("updated_at")
                ).returning(h.c.seq, h.c.hint_id)).one()
            if scope_dossier_ids:
                c.execute(insert(T.hint_scope), [
                    {"seq": seq, "dossier_id": x} 
                    for x in sorted(set(scope_dossier_ids))
                    ])
            self._hint_message(c, hid, department, "submitted", 1, 1)
            return hid

    def get_hint(self, hint_id) -> dict[str, Any]:
        r = self._one(select(T.hints).where(T.hints.c.hint_id == hint_id))
        if not r:
            raise KeyError(hint_id)
        return r

    def list_hints(self, department=None, status=None, type=None) -> list[dict[str, Any]]:
        h = T.hints
        q = select(h).order_by(h.c.seq)
        for col, v in ((h.c.department, department), (h.c.status, status), (h.c.type, type)):
            if v:
                q = q.where(col == v)
        return self._all(q)

    def set_hint_status(self, hint_id, new_status, expected_row_version, *, 
                        actor_oid=None, actor_name=None, reason=None, 
                        check_results=None, acl_groups=None) -> int:
        """One method for every status move. Enforces the transitions, the four-eyes rule and optimistic concurrency."""
        h = T.hints
        with self._tx() as c:
            r = c.execute(select(h).where(h.c.hint_id == hint_id).with_for_update()).first()
            if r is None:
                raise KeyError(hint_id)
            if r.row_version != expected_row_version:
                raise ValueError("set_hint_status: the hint changed since it was read")
            if (r.status, new_status) not in self._MOVES and not (r.type == "transcription_fix" and r.status == "submitted" and new_status in ("published", "rejected")):
                raise ValueError(f"set_hint_status: that status move is not allowed: {r.status} -> {new_status}")
            if new_status in ("approved", "rejected", "revoked") and actor_oid is None:
                raise ValueError("set_hint_status: a steward must be named")
            if new_status == "approved" and str(actor_oid).lower() == r.author_oid:
                raise PermissionError("the author cannot approve their own hint")
            vals: dict[str, Any] = {"status": new_status, "row_version": h.c.row_version + 1, "updated_at": self._now()}
            if check_results is not None:
                vals["check_results"] = check_results
            if acl_groups is not None:
                vals["acl_groups"] = list(acl_groups)
            if reason is not None:
                vals["decision_reason"] = reason
            if new_status == "approved":
                vals |= {"approved_by_oid": actor_oid, "approved_by_name": actor_name, "approved_at": self._now(),
                        "review_by": cast(self._now() + timedelta(days=365), SaDate)}
            c.execute(update(h).where(h.c.seq == r.seq).values(**vals))
            self._hint_message(c, hint_id, r.department, new_status, r.version, r.row_version + 1)
            return r.row_version + 1

    def edit_hint(self, hint_id, expected_row_version, text, editor_name) -> int:
        """A steward's edit of the wording: version + 1, same status. No message: there is nothing for the worker to do."""
        h = T.hints
        rv = self._exec_returning(update(h).where(
            h.c.hint_id == hint_id, 
            h.c.row_version == expected_row_version, 
            h.c.status == "awaiting_approval"
            ).values(
                text=text, 
                version=h.c.version + 1, 
                row_version=h.c.row_version + 1, 
                editor_name=editor_name, 
                updated_at=self._now()
                ).returning(h.c.row_version)
            )
        if rv is None:
            raise ValueError("edit_hint: the hint changed or is no longer awaiting approval")
        return rv

    def record_publication(self, hint_id, destination, action, reason="approval") -> None:
        h, p = T.hints, T.hint_publications
        now = self._now()
        n = self._exec(insert(p).from_select(
            ["hint_seq", "hint_version", "destination", "action", "reason", "at"],
            select(h.c.seq, h.c.version, 
                literal(destination), 
                literal(action), 
                literal(reason), 
                literal(now) 
                if self.clock else now
                ).where(
                    h.c.hint_id == hint_id
                    )
                )
            )
        if n == 0:
            raise KeyError(hint_id)

    def record_acl_audit(self, *, hint_id=None, dossier_id=None, 
                        changed_by, reason, old_acl, new_acl, widened) -> None:
        self._exec(insert(T.acl_audit).values(
            dossier_id=dossier_id, hint_id=hint_id, 
            changed_by=changed_by, reason=reason, old_acl=list(old_acl),
            new_acl=list(new_acl), widened=widened
            ))

    def hints_anchored_to(self, dossier_id) -> list[dict[str, Any]]:
        h, s = T.hints, T.hint_scope
        return self._all(select(h).join(
            s, s.c.seq == h.c.seq).where(
                s.c.dossier_id == dossier_id, 
                h.c.status == "published"
                ).order_by(h.c.seq))

    # inbox
    def add_inbox(self, *, recipient_kind, recipient_value, 
                type, title, body="", link=None, event_id=None) -> bool:
        i = T.inbox
        row = self._one(pg_insert(i).values(
            recipient_kind=recipient_kind, 
            recipient_value=recipient_value, 
            type=type, title=title, body=body, 
            link=link, event_id=event_id, 
            **self._stamp("created_at")
            ).on_conflict_do_nothing(
                index_elements=[i.c.event_id, i.c.recipient_kind, i.c.recipient_value], 
                index_where=i.c.event_id.is_not(None)
                ).returning(i.c.id))
        return row is not None  # None: the notifier already stored this event for this recipient

    def inbox_for(self, user_oid, steward_departments, 
                is_admin, unread_only=False) -> list[dict[str, Any]]:
        i = T.inbox
        conds = [and_(i.c.recipient_kind == "user", i.c.recipient_value == str(user_oid))]
        if steward_departments:
            conds.append(and_(
                i.c.recipient_kind == "steward", 
                i.c.recipient_value.in_(steward_departments)
                ))
        if is_admin:
            conds.append(i.c.recipient_kind == "admin")
        q = select(i).where(or_(*conds)).order_by(i.c.id.desc())
        return self._all(q.where(i.c.read_at.is_(None)) if unread_only else q)

    def mark_inbox_read(self, inbox_id) -> None:
        self._exec(update(T.inbox).where(T.inbox.c.id == inbox_id).values(read_at=self._now()))

    # uploads
    def create_upload(self, *, department, mode, dossier_id, 
                    uploaded_by_oid, uploaded_by_name, files, block_bytes) -> str:
        with self._tx() as c:
            uid = f"up-{self._pynow():%Y%m%d}-{c.execute(select(T.seq_upload.next_value())).scalar():04d}"
            c.execute(insert(T.uploads).values(
                upload_id=uid, department=department, 
                mode=mode, dossier_id=dossier_id, 
                uploaded_by_oid=uploaded_by_oid,
                uploaded_by_name=uploaded_by_name, 
                **self._stamp("created_at"), 
                **self._stamp("last_activity_at")
                ))
            if files:
                c.execute(insert(T.upload_files), 
                        [{
                            "upload_id": uid, 
                            "name": f["name"], 
                            "bytes": f["bytes"], 
                            "sha256": f["sha256"],
                            "blocks_total": max(1, -(-f["bytes"] // block_bytes))
                        } for f in files
                        ])
            return uid

    def get_upload(self, upload_id) -> dict[str, Any]:
        u, f = T.uploads, T.upload_files
        r = self._one(select(u).where(u.c.upload_id == upload_id))
        if not r:
            raise KeyError(upload_id)
        r["files"] = [{**x, "sha256": x["sha256"].strip()} 
                    for x in self._all(
                        select(f).where(
                            f.c.upload_id == upload_id
                            ).order_by(f.c.name)
                        )]
        return r

    def set_upload_status(self, upload_id, status, reject_reason=None) -> None:
        u = T.uploads
        self._exec(update(u).where(
            u.c.upload_id == upload_id
            ).values(
                status=status, 
                reject_reason=func.coalesce(
                    reject_reason, 
                    u.c.reject_reason
                    ), 
                last_activity_at=self._now()
                )
            )

    def touch_upload(self, upload_id) -> None:
        self._exec(update(T.uploads).where(
            T.uploads.c.upload_id == upload_id
            ).values(
                last_activity_at=self._now()
                )
            )

    def bump_scan_attempt(self, upload_id) -> int:
        u = T.uploads
        return int(self._exec_returning(update(u).where(
            u.c.upload_id == upload_id
            ).values(
                scan_attempt=u.c.scan_attempt + 1
                ).returning(u.c.scan_attempt)
            ))

    def latest_revision(self, dossier_id) -> int:
        d = T.dossiers
        return int(self._exec_returning(
            select(
                func.coalesce(func.max(d.c.revision), 0)
                ).where(d.c.dossier_id == dossier_id)
            ))

    def add_upload_dossier(self, upload_id, dossier_id, revision, manifest_hash) -> None:
        self._exec(
            pg_insert(T.upload_dossiers).values(
                upload_id=upload_id, 
                dossier_id=dossier_id, 
                revision=revision, 
                manifest_hash=manifest_hash
                ).on_conflict_do_nothing()
            )

    def upload_dossiers(self, upload_id) -> list[dict[str, Any]]:
        d = T.upload_dossiers
        return [
            {
                **r, 
                "manifest_hash": r["manifest_hash"].strip(), 
                "intake_sent": int(r["intake_sent"])
            }
                for r in self._all(select(d).where(
                    d.c.upload_id == upload_id
                    ).order_by(d.c.dossier_id))
                ]

    def mark_intake_sent(self, upload_id, dossier_id) -> None:
        d = T.upload_dossiers
        self._exec(update(d).where(
            d.c.upload_id == upload_id, 
            d.c.dossier_id == dossier_id
            ).values(intake_sent=True)
                )

    def next_unfiled_seq(self) -> int:
        return int(self._exec_returning(select(T.seq_unfiled.next_value())))

    def expire_uploads(self, older_than_days) -> list[str]:
        u = T.uploads
        with self._tx() as c:
            return [r[0] for r in c.execute(
                update(u).where(
                    u.c.status == "open", 
                    u.c.last_activity_at < self._now() - timedelta(days=older_than_days)
                    ).values(
                        status="expired", 
                        last_activity_at=self._now()
                        ).returning(u.c.upload_id)
                    )]

    # watchdog
    def stuck_pages(self, older_than_minutes, limit=200) -> list[dict[str, Any]]:
        p = T.pages
        return self._all(
            select(p).where(
                p.c.status.not_in(FINAL_PAGE), 
                p.c.updated_at < self._now() - timedelta(minutes=older_than_minutes)
                ).order_by(p.c.updated_at).limit(limit)
            )

    def bump_page_resend(self, dossier_id, revision, page_no) -> int:
        p = T.pages
        return int(self._exec_returning(
            update(p).where(
                p.c.dossier_id == dossier_id, 
                p.c.revision == revision, 
                p.c.page_no == page_no
                ).values(
                    resend_count=p.c.resend_count + 1, 
                    updated_at=self._now()).returning(p.c.resend_count)
                ))

    # test helpers: so behaviour tests do not depend on the SQL dialect
    def debug_rows(self, table: str, **where: Any) -> list[dict[str, Any]]:
        t = T.metadata.tables[f"{T.SCHEMA}.{table}"]
        return self._all(select(t).where(*[t.c[k] == v for k, v in where.items()]))

    def debug_set_claims(self, department: str, claims: int) -> None:
        dc = T.department_counters
        self._exec(pg_insert(dc).values(
            department=department, 
            claims=claims
            ).on_conflict_do_update(
                index_elements=[dc.c.department],
                set_={"claims": claims}
                )
            )


def ops_store(settings) -> SqlOps:
    """The store for the `database` settings: a plain URL locally, an Entra-token engine in Azure."""
    return SqlOps(
        settings.database.sqlalchemy_url, 
        engine=engine_for(settings.database)
        )
