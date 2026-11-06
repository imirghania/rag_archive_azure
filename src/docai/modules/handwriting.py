"""job-handwriting-online: the independent second reading of every flagged line (spec, Workflow 1, Step 5).

The model sees only the crop image and a language hint. Nothing in this module can pass it the OCR text."""
from __future__ import annotations

import hashlib

from docai.contracts import keys, messageids
from docai.contracts.artifacts import VlmReading
from docai.contracts.messages import Envelope, SecondReadRequested, parse_payload
from docai.documents.artifactio import write_model
from docai.ports import AlreadyExists
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, SecondReadRequested)
    dossier_id, rev = revision_of(env)
    pref = keys.PageRef.parse(env.subject)
    second: dict[str, str] = {}
    for ln in req.lines:
        path = f"{pref.dir}crops/{ln.line_id}.vlm.json"
        second[ln.line_id] = f"crops/{ln.line_id}.vlm.json"
        if ctx.blobs.exists("extracted", path):
            continue  # already read: do not call the model again
        crop = ctx.blobs.read("extracted", pref.dir + ln.crop)
        out = ctx.vision.transcribe(crop, lang_hint=ln.lang_hint, line_key=keys.line_key(pref.key, ln.line_id))
        reading = VlmReading(line_key=keys.line_key(pref.key, ln.line_id), text=out.text, lang=out.lang, uncertain=out.uncertain,
                             model=ctx.settings.models.second_reader, crop_sha256=hashlib.sha256(crop).hexdigest(), read_at=ctx.clock.now())
        try:
            write_model(ctx.blobs, "extracted", path, reading, once=True)
        except AlreadyExists:
            pass
    send(ctx, envelope("page.reconcile.requested", pref.key, department=env.department, dossier_id=dossier_id, revision=rev, payload={
        "page_no": pref.page_no, "page_dir": pref.dir, "second_reads": second, "expected_second_reads": len(req.lines)}),
         message_id=messageids.message_id("reconcile", pref.key))


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
