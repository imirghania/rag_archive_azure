"""job-post-review: rebuilds a page after a human decision and starts re-indexing (spec, Workflow 4, Step 5).

The job never edits a lines file. It folds: start from the base file `lines.v1.json`, apply every decision that has
been applied up to this version, in time order, and write `lines.v{n}.json` and `page.v{n}.md`."""
from __future__ import annotations

import re

from docai.contracts import keys, messageids
from docai.contracts.artifacts import DecisionFile, LinesFile
from docai.contracts.messages import Envelope, ReviewDecided, parse_payload
from docai.documents.artifactio import read_model, write_model
from docai.documents.linetext import render_markdown
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send


def fold(base: LinesFile, decisions: list[DecisionFile], version: int) -> LinesFile:
    lf = base.model_copy(deep=True)
    lf.version = version
    for d in sorted(decisions, key=lambda x: x.at):
        line = lf.line(d.line_key.rsplit("/", 1)[1])
        line.tier = d.tier
        line.text = d.text if d.text is not None else "[illegible]"
        line.candidates, line.source, line.decision_file = [], "human", None
    return lf


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, ReviewDecided)
    dossier_id, rev = revision_of(env)
    dept = keys.department_of(dossier_id)
    ref = keys.LineRef.parse(env.subject)
    # A redelivery gets the stored version back and finishes the work again: every write below is deterministic and the
    # next message is deduplicated, so a crash after the version was raised can never lose the downstream message.
    version, _ = ctx.ops.apply_decision(req.task_id, req.document_id)
    applied = {t: v for t, v in ctx.ops.applied_tasks(req.document_id).items() if v <= version}

    pdir = ref.page.dir
    base = read_model(ctx.blobs, "extracted", pdir + "lines.v1.json", LinesFile)
    decisions = []
    for path in ctx.blobs.list("extracted", pdir):
        if re.search(r"/L\d+\.decision\.[0-9a-f]+\.json$", "/" + path.removeprefix(pdir)):
            d = read_model(ctx.blobs, "extracted", path, DecisionFile)
            if d.task_id in applied:
                decisions.append(d)
    lf = fold(base, decisions, version)
    write_model(ctx.blobs, "extracted", f"{pdir}lines.v{version}.json", lf)
    ctx.blobs.write("extracted", f"{pdir}page.v{version}.md", render_markdown(lf).encode("utf-8"), overwrite=True)

    send(ctx, envelope("document.chunk.requested", req.document_id, department=dept, dossier_id=dossier_id, revision=rev,
                       payload={"document_id": req.document_id, "version": version}),
         message_id=messageids.message_id("chunk", req.document_id, version=version), document_id=req.document_id)


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
