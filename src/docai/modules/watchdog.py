"""job-watchdog: finds work that is stuck and resends or fails it (spec, Failures). Runs every ten minutes.

It only peeks at dead-letter queues, never receives from them. A resent message needs a new MessageId, or Service Bus
would drop it as a duplicate of the lost one; the step's own idempotency makes a second delivery harmless."""
from __future__ import annotations

from dataclasses import dataclass, field

from docai.contracts import keys, messageids
from docai.contracts.artifacts import Box, Line, LinesFile, Triage
from docai.contracts.enums import PageStatus, TrustTier
from docai.contracts.messages import QUEUES
from docai.documents.artifactio import read_model, write_model
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, send

PAGE_QUEUES = ("q-ocr-online", "q-handwriting-online", "q-reconcile")
PLACEHOLDER = "[page unreadable: {reason}]"


@dataclass
class Report:
    resent: int = 0
    failed_pages: int = 0
    segment_sent: int = 0
    intake_failed: list[str] = field(default_factory=list)
    dead_letters: dict[str, int] = field(default_factory=dict)
    purged_conversations: int = 0
    expired_uploads: int = 0


def run(ctx: Context) -> Report:
    tun = ctx.settings.tuning
    rep = Report()
    for p in ctx.ops.stuck_pages(tun.watchdog_page_stuck_minutes):
        d, rev, n = p["dossier_id"], p["revision"], p["page_no"]
        if p["resend_count"] >= tun.watchdog_max_resends:
            _fail_page(ctx, d, rev, n, "stuck_after_resends", rep)
        else:
            attempt = ctx.ops.bump_page_resend(d, rev, n)
            _resend(ctx, p, attempt)
            rep.resent += 1
    for q in QUEUES:  # peek only
        dead = ctx.queue.peek_dead_letters(q)
        if dead:
            rep.dead_letters[q] = len(dead)
        if q in PAGE_QUEUES:
            for m in dead:  # a message that used up its five deliveries must not hold the dossier back
                ref = keys.PageRef.parse(m.envelope.subject)
                _fail_page(ctx, ref.dossier_id, ref.revision, ref.page_no, "dead_letter", rep)
        elif q == "q-intake":
            for m in dead:
                dossier = m.envelope.dossier_id or m.envelope.subject
                send(ctx, envelope("dossier.failed", dossier, department=m.envelope.department, dossier_id=dossier,
                                   payload={"reason": "failed_intake: the files did not match the manifest or were missing"}),
                     message_id=f"failed-intake:{m.message_id}")
                rep.intake_failed.append(dossier)
    rep.purged_conversations = ctx.ops.purge_conversations(tun.conversations_retention_days)
    rep.expired_uploads = len(ctx.ops.expire_uploads(tun.upload_expire_days))
    return rep


def _resend(ctx: Context, p: dict, attempt: int) -> None:
    ref = keys.PageRef(p["dossier_id"], p["revision"], p["page_no"])
    common = dict(department=ref.department, dossier_id=ref.dossier_id, revision=ref.revision)
    if p["status"] == PageStatus.preprocessed.value:
        step, queue_msg = "ocr", envelope("page.ocr.requested", ref.key, **common, payload={
            "page_no": ref.page_no, "page_dir": ref.dir, "image": "page.png", "text_layer": bool(p["text_layer"])})
    elif p["status"] == PageStatus.awaiting_second_read.value:
        tri = read_model(ctx.blobs, "extracted", ref.dir + "triage.json", Triage)
        step, queue_msg = "second-read", envelope("page.second-read.requested", ref.key, **common, payload={
            "page_no": ref.page_no, "page_dir": ref.dir, "page_image_sha256": tri.page_image_sha256,
            "lines": [{"line_id": t.id, "crop": t.crop, "lang_hint": t.lang} for t in tri.flagged()]})
    else:  # ocr_done: nothing needed a second read
        step, queue_msg = "reconcile", envelope("page.reconcile.requested", ref.key, **common, payload={
            "page_no": ref.page_no, "page_dir": ref.dir, "second_reads": {}, "expected_second_reads": 0})
    send(ctx, queue_msg, message_id=messageids.resend(messageids.message_id(step, ref.key), attempt))


def _fail_page(ctx: Context, dossier_id: str, rev: int, page_no: int, reason: str, rep: Report) -> None:
    """A page that can never be read is final. It gets the placeholder so page numbers stay aligned and the gap is visible."""
    ref = keys.PageRef(dossier_id, rev, page_no)
    done = ctx.ops.finish_page(dossier_id, rev, page_no, "failed", reason)
    if done is None:
        return  # already final: a redelivery changes nothing
    rep.failed_pages += 1
    ph = Line(id="L1", text=PLACEHOLDER.format(reason=reason), tier=TrustTier.missing, style="printed", box=Box(x0=0, y0=0, x1=1, y1=1), source="placeholder")
    write_model(ctx.blobs, "extracted", ref.dir + "lines.v1.json", LinesFile(page_key=ref.key, page_no=page_no, lines=[ph]))
    ctx.blobs.write("extracted", ref.dir + "page.v1.md", (ph.text + "\n").encode(), overwrite=True)
    if done[0] == done[1]:  # this call closed the last open page of the revision
        dkey = keys.dossier_key(dossier_id, rev)
        send(ctx, envelope("dossier.segment.requested", dkey, department=ref.department, dossier_id=dossier_id, revision=rev),
             message_id=messageids.message_id("segment", dkey))
        rep.segment_sent += 1


def handle(ctx: Context, env=None) -> None:  # entry point for the scheduled job
    run(ctx)


if __name__ == "__main__":
    from docai.runtime.launch import scheduled

    scheduled(run)
