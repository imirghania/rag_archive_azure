"""app-review, service layer: claim a task under a lease, show the evidence, record a decision, relay the outbox
(spec, Workflow 4). The HTTP endpoints and sign-in wrap these functions later; `departments` is always the set of
departments where the caller holds the expert or steward capability, worked out by the auth library, never taken
from the request."""
from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from docai.contracts import keys, messageids
from docai.contracts.artifacts import DecisionFile, Readings
from docai.contracts.enums import Capability, Decision, HintStatus, TrustTier
from docai.contracts.messages import Envelope
from docai.documents.artifactio import read_model, write_model
from docai.ports import AlreadyExists, LeaseLost
from docai.runtime.context import Context
from docai.runtime.hintacl import hint_audience
from docai.runtime.http import make_principal_dep, new_app
from docai.runtime.messaging import envelope, send
from docai.security.access import Principal, departments_with, require


class ReviewError(Exception):
    pass


@dataclass
class Evidence:
    task: dict
    crop: bytes
    context_crop: bytes
    readings: Readings


def claim_next(ctx: Context, user_oid: str, departments: list[str]) -> dict | None:
    """The next task for this person: highest demand first, every fifth claim the oldest. None when nothing is open."""
    if not departments:
        return None
    ctx.ops.set_departments(departments)
    t = ctx.settings.tuning
    task = ctx.ops.claim_task(user_oid, departments, lease_minutes=t.review_lease_minutes, escalate_after=t.review_escalate_after_abandons,
                              oldest_every=t.review_oldest_every_nth_claim, window_days=t.review_demand_window_days)
    # shortcut: escalations are noticed when someone next claims; the MessageId makes the announcement happen once. A sweep
    # in the watchdog would announce them even when nobody claims.
    for esc in ctx.ops.list_tasks(status="escalated"):
        if esc["department"] in departments:
            send(ctx, envelope("review.escalated", esc["line_key"], department=esc["department"], dossier_id=esc["dossier_id"], revision=esc["revision"],
                               payload={"task_id": esc["task_id"]}), message_id=f"escalated:{esc['task_id']}")
    return task


def claim_escalated(ctx: Context, user_oid: str, departments: list[str]) -> dict | None:
    """The Escalated tab: a steward takes a task that experts abandoned three times."""
    if not departments:
        return None
    ctx.ops.set_departments(departments)
    return ctx.ops.claim_task(user_oid, departments, lease_minutes=ctx.settings.tuning.review_lease_minutes, from_status="escalated")


def _own_task(ctx: Context, task_id: int, departments: list[str]) -> dict:
    ctx.ops.set_departments(departments)  # row-level security: the task of another department is then invisible, not just refused
    task = ctx.ops.get_task(task_id)
    if task["department"] not in departments:
        raise PermissionError(f"task {task_id} belongs to another department")
    return task


def heartbeat(ctx: Context, task_id: int, lease_token: str, departments: list[str]):
    _own_task(ctx, task_id, departments)
    return ctx.ops.renew_lease(task_id, lease_token, ctx.settings.tuning.review_lease_minutes)


def evidence(ctx: Context, task_id: int, departments: list[str]) -> Evidence:
    """Both readings and the crops. The browser never gets a storage address: the app reads with its own identity."""
    task = _own_task(ctx, task_id, departments)
    pdir = keys.PageRef(task["dossier_id"], task["revision"], task["page_no"]).dir
    return Evidence(task, ctx.blobs.read("extracted", f"{pdir}crops/{task['line_id']}.png"),
                    ctx.blobs.read("extracted", f"{pdir}crops/{task['line_id']}.ctx.png"),
                    read_model(ctx.blobs, "extracted", f"{pdir}{task['line_id']}.readings.json", Readings))


def decide(ctx: Context, *, task_id: int, lease_token: str, user_oid: str, user_name: str, departments: list[str],
           decision: Decision, text: str | None = None) -> None:
    """Writes the decision file (once), then closes the task and queues `review.decided` in one SQL transaction."""
    task = _own_task(ctx, task_id, departments)
    if task["status"] != "claimed" or task["lease_token"] != lease_token:
        raise LeaseLost(f"task {task_id} was reassigned or closed")
    pdir = keys.PageRef(task["dossier_id"], task["revision"], task["page_no"]).dir
    readings = read_model(ctx.blobs, "extracted", f"{pdir}{task['line_id']}.readings.json", Readings) if decision in (
        Decision.accept_ocr, Decision.accept_model) else None
    if decision is Decision.accept_ocr:
        final = next(r.text for r in readings.readings if r.engine == "ocr")
    elif decision is Decision.accept_model:
        final = next(r.text for r in readings.readings if r.engine == "second_reader")
    elif decision is Decision.correct:
        final = (text or "").strip()
        if not final:
            raise ReviewError("a correction needs text")
    else:
        final = None
    tier = TrustTier.illegible if decision is Decision.illegible else TrustTier.human_verified
    path = f"{pdir}{task['line_id']}.decision.{lease_token[:8]}.json"
    try:  # If-None-Match: a decision file can never be overwritten
        write_model(ctx.blobs, "extracted", path, DecisionFile(
            task_id=task_id, line_key=task["line_key"], decision=decision, text=final, tier=tier, by_oid=user_oid, by_name=user_name,
            at=ctx.clock.now(), lease_token=lease_token), once=True)
    except AlreadyExists:
        pass  # a retry after a crash between the file and the SQL transaction
    ctx.ops.decide_task(task_id, lease_token, decision.value, user_oid, {
        "task_id": task_id, "decision": decision.value, "text": final, "decision_file": f"{keys.extracted_dossier_dir(task['dossier_id'], task['revision'])}"
        f"p{task['page_no']:03d}/{task['line_id']}.decision.{lease_token[:8]}.json", "document_id": task["document_id"]})
    if task.get("hint_id"):  # the review task came from an expert's transcription fix: record its outcome on the hint
        h = ctx.ops.get_hint(task["hint_id"])
        agreed = final is not None and final.strip() == (task.get("suggested_text") or "").strip()
        ctx.ops.set_hint_status(h["hint_id"], HintStatus.published.value if agreed else HintStatus.rejected.value, h["row_version"], actor_oid=user_oid,
                                actor_name=user_name, reason=None if agreed else "The reviewer read the line differently from the suggestion")


def relay_outbox(ctx: Context, limit: int = 100) -> int:
    """Sends every pending outbox row, whoever wrote it, using each message_id as the Service Bus MessageId.
    A crash between sending and marking resends the row; Service Bus drops the duplicate."""
    n = 0
    for row in ctx.ops.pending_outbox(limit):
        env = Envelope.from_json(row.body)
        ctx.queue.send(row.destination, env, message_id=row.message_id, session_id=row.session_id)
        ctx.ops.mark_outbox_sent(row.id)
        n += 1
    return n


# ---------------------------------------------------------------------------------------------- hints (steward side)
def hints_awaiting(ctx: Context, p: Principal) -> list[dict]:
    """The Hints tab: awaiting approval in the departments where the caller is a steward, with the check results and the audience."""
    registry = ctx.ops.registered_groups()
    from docai.security.access import departments_with
    out = []
    for dept in departments_with(registry, p, Capability.approve):
        for h in ctx.ops.list_hints(dept, HintStatus.awaiting_approval.value):
            out.append({**h, "audience": hint_audience(ctx, h)})  # the steward sees who will read it before approving
    return out


def _steward_hint(ctx: Context, p: Principal, hint_id: str) -> dict:
    h = ctx.ops.get_hint(hint_id)
    require(ctx.ops.registered_groups(), p, Capability.approve, h["department"])
    return h


def approve_hint(ctx: Context, p: Principal, hint_id: str, *, widen_to: list[str] | None = None, widen_reason: str | None = None) -> None:
    """The four-eyes rule is enforced twice: the Approve button is hidden for the author, and the store refuses it independently."""
    h = _steward_hint(ctx, p, hint_id)
    acl = None
    if widen_to is not None:
        if not (widen_reason or "").strip():
            raise ReviewError("widening a note needs a reason")
        acl = sorted(set(widen_to))
        ctx.ops.record_acl_audit(hint_id=hint_id, changed_by=p.name, reason=widen_reason, old_acl=hint_audience(ctx, h), new_acl=acl, widened=True)
    ctx.ops.set_hint_status(hint_id, HintStatus.approved.value, h["row_version"], actor_oid=p.oid, actor_name=p.name, acl_groups=acl)


def reject_hint(ctx: Context, p: Principal, hint_id: str, reason: str) -> None:
    h = _steward_hint(ctx, p, hint_id)
    if not reason.strip():
        raise ReviewError("a rejection needs a reason, because the author is told why")
    ctx.ops.set_hint_status(hint_id, HintStatus.rejected.value, h["row_version"], actor_oid=p.oid, actor_name=p.name, reason=reason)


def revoke_hint(ctx: Context, p: Principal, hint_id: str, reason: str) -> None:
    h = _steward_hint(ctx, p, hint_id)  # stewards only: an expert cannot revoke, not even their own hint
    ctx.ops.set_hint_status(hint_id, HintStatus.revoked.value, h["row_version"], actor_oid=p.oid, actor_name=p.name, reason=reason)


def edit_hint(ctx: Context, p: Principal, hint_id: str, text: str) -> None:
    h = _steward_hint(ctx, p, hint_id)
    ctx.ops.edit_hint(hint_id, h["row_version"], text, p.name)


# ---------------------------------------------------------------------------------------------- access, reprocess, admin
def restrict_dossier(ctx: Context, p: Principal, dossier_id: str, new_acl: list[str], reason: str) -> int:
    """A steward narrows or reshapes who may read a dossier inside the department (Workflow 8). Every group must belong to the
    department: sharing with another department needs that department's steward as well, which the MVP does not offer."""
    dept = keys.department_of(dossier_id)
    registry = ctx.ops.registered_groups()
    require(registry, p, Capability.approve, dept)
    if not new_acl or not (reason or "").strip():
        raise ReviewError("a restriction needs at least one group and a reason")
    foreign = [g for g in new_acl if registry.get(g, (None,))[0] != dept]
    if foreign:
        raise PermissionError("widening beyond the department needs the receiving department's steward")
    old = ctx.ops.dossier_acl(dossier_id)
    return ctx.ops.change_dossier_acl(dossier_id, sorted(set(new_acl)), p.name, reason, widened=bool(set(new_acl) - set(old)))


def request_reprocess(ctx: Context, p: Principal, dossier_id: str) -> int:
    """An administrator starts a new revision from the files already in `raw` (Workflow 8). Goes through the outbox."""
    from docai.security.access import is_admin
    if not is_admin(p):
        raise PermissionError("reprocessing needs the admin role")
    latest = ctx.ops.latest_revision(dossier_id)
    if latest == 0:
        raise KeyError(dossier_id)
    env = envelope("dossier.reprocess.requested", dossier_id, department=keys.department_of(dossier_id), dossier_id=dossier_id,
                   payload={"requested_by": p.name, "from_revision": latest})
    ctx.ops.enqueue(messageids.reprocess(dossier_id, latest + 1), "q-intake", env.to_json())
    return latest + 1


def dossier_status(ctx: Context, p: Principal, status: str | None = None) -> list[dict]:
    """The Admin page: statuses and counts, never content."""
    from docai.security.access import is_admin
    if not is_admin(p):
        raise PermissionError("the status page needs the admin role")
    return ctx.ops.list_dossiers(status=status)


def inbox(ctx: Context, p: Principal) -> list[dict]:
    from docai.security.access import departments_with
    return ctx.ops.inbox_for(p.oid, departments_with(ctx.ops.registered_groups(), p, Capability.approve), is_admin_(p))


def is_admin_(p: Principal) -> bool:
    from docai.security.access import is_admin
    return is_admin(p)


# ---------------------------------------------------------------------------------------------- HTTP
class Heartbeat(BaseModel):
    lease_token: str


class DecideRequest(BaseModel):
    lease_token: str
    decision: Decision
    text: str | None = None


class ReasonRequest(BaseModel):
    reason: str = ""


class ApproveRequest(BaseModel):
    widen_to: list[str] | None = None
    widen_reason: str | None = None


class EditRequest(BaseModel):
    text: str


class AclRequest(BaseModel):
    groups: list[str]
    reason: str


class ReprocessRequest(BaseModel):
    dossier_id: str


def _task_json(t: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in t.items() if k in (
        "task_id", "department", "dossier_id", "revision", "page_no", "line_id", "line_key", "reason", "suggested_text", "lease_token", "lease_expires_at")}


def start_relay(ctx: Context, interval: float = 2.0) -> threading.Event:
    """The outbox relay loop: sends pending rows every two seconds. It runs inside this app, which is why the app keeps a replica."""
    stop = threading.Event()

    def loop():
        while not stop.wait(interval):
            try:
                relay_outbox(ctx)
            except Exception:  # noqa: BLE001 - a failed pass is retried by the next one; rows stay pending
                import logging
                logging.getLogger("docai.relay").exception("outbox relay pass failed")
    threading.Thread(target=loop, name="outbox-relay", daemon=True).start()
    return stop


def create_app(ctx: Context, *, relay: bool = False):
    app, principal = new_app("app-review"), make_principal_dep(ctx)
    if relay:  # Starlette 1.x has no startup handlers (add_event_handler, on_event): only a lifespan, D50
        @contextlib.asynccontextmanager
        async def lifespan(_app):
            stop = start_relay(ctx)
            try:
                yield
            finally:
                stop.set()
        app.router.lifespan_context = lifespan

    def depts(p: Principal, cap: Capability) -> list[str]:
        return departments_with(ctx.ops.registered_groups(), p, cap)

    def lost(e: LeaseLost):
        return HTTPException(409, "the task was reassigned or closed")

    @app.get("/api/review/next")
    def nxt(p: Principal = Depends(principal)):
        t = claim_next(ctx, p.oid, depts(p, Capability.review))
        return _task_json(t) if t else Response(status_code=204)

    @app.get("/api/review/escalated/next")
    def esc(p: Principal = Depends(principal)):
        t = claim_escalated(ctx, p.oid, depts(p, Capability.approve))
        return _task_json(t) if t else Response(status_code=204)

    allowed = lambda p: sorted(set(depts(p, Capability.review)) | set(depts(p, Capability.approve)))  # noqa: E731

    @app.post("/api/review/{task_id}/heartbeat")
    def beat(task_id: int, h: Heartbeat, p: Principal = Depends(principal)):
        exp = heartbeat(ctx, task_id, h.lease_token, allowed(p))
        if exp is None:
            raise lost(LeaseLost())
        return {"lease_expires_at": exp.isoformat()}

    @app.get("/api/review/{task_id}/evidence")
    def ev(task_id: int, p: Principal = Depends(principal)):
        e = evidence(ctx, task_id, allowed(p))
        return {"task": _task_json(e.task), "readings": [r.model_dump() for r in e.readings.readings]}

    @app.get("/api/review/{task_id}/crop")
    def crop(task_id: int, context: bool = False, p: Principal = Depends(principal)):
        e = evidence(ctx, task_id, allowed(p))
        return Response(e.context_crop if context else e.crop, media_type="image/png")

    @app.post("/api/review/{task_id}/decide")
    def decide_(task_id: int, req: DecideRequest, p: Principal = Depends(principal)):
        try:
            decide(ctx, task_id=task_id, lease_token=req.lease_token, user_oid=p.oid, user_name=p.name, departments=allowed(p), decision=req.decision, text=req.text)
        except LeaseLost as e:
            raise lost(e) from e
        except ReviewError as e:
            raise HTTPException(422, str(e)) from e
        return {"ok": True}

    @app.get("/api/hints/awaiting")
    def awaiting(p: Principal = Depends(principal)):
        return hints_awaiting(ctx, p)

    def wrap(fn, *a, **kw):
        try:
            fn(*a, **kw)
        except ReviewError as e:
            raise HTTPException(422, str(e)) from e
        except ValueError as e:  # the store: stale row version or a move that is not allowed
            raise HTTPException(409, str(e)) from e
        return {"ok": True}

    @app.post("/api/hints/{hint_id}/approve")
    def approve(hint_id: str, req: ApproveRequest, p: Principal = Depends(principal)):
        return wrap(approve_hint, ctx, p, hint_id, widen_to=req.widen_to, widen_reason=req.widen_reason)

    @app.post("/api/hints/{hint_id}/reject")
    def reject(hint_id: str, req: ReasonRequest, p: Principal = Depends(principal)):
        return wrap(reject_hint, ctx, p, hint_id, req.reason)

    @app.post("/api/hints/{hint_id}/revoke")
    def revoke(hint_id: str, req: ReasonRequest, p: Principal = Depends(principal)):
        return wrap(revoke_hint, ctx, p, hint_id, req.reason)

    @app.post("/api/hints/{hint_id}/edit")
    def edit(hint_id: str, req: EditRequest, p: Principal = Depends(principal)):
        return wrap(edit_hint, ctx, p, hint_id, req.text)

    @app.post("/api/dossiers/{dossier_id}/acl")
    def acl(dossier_id: str, req: AclRequest, p: Principal = Depends(principal)):
        try:
            return {"acl_version": restrict_dossier(ctx, p, dossier_id, req.groups, req.reason)}
        except ReviewError as e:
            raise HTTPException(422, str(e)) from e

    @app.get("/api/inbox")
    def inbox_(p: Principal = Depends(principal)):
        return inbox(ctx, p)

    @app.post("/api/inbox/{inbox_id}/read")
    def read(inbox_id: int, p: Principal = Depends(principal)):
        if inbox_id not in {r["id"] for r in inbox(ctx, p)}:
            raise KeyError(inbox_id)  # somebody else's row looks like a missing one
        ctx.ops.mark_inbox_read(inbox_id)
        return {"ok": True}

    @app.get("/api/admin/status")
    def status_(status: str | None = None, p: Principal = Depends(principal)):
        return dossier_status(ctx, p, status)

    @app.post("/api/admin/reprocess")
    def reprocess(req: ReprocessRequest, p: Principal = Depends(principal)):
        return {"revision": request_reprocess(ctx, p, req.dossier_id)}

    return app


if __name__ == "__main__":
    from docai.runtime.launch import http_app

    http_app(create_app, relay=True)  # the outbox relay loop runs inside this app
