"""job-segment: finds the logical documents inside a dossier (spec, Workflow 1, Step 7).

Fixed cues first; the model is asked only when the cues are inconclusive, and must quote the lines it relies on."""
from __future__ import annotations

import json
import re

from docai.contracts import keys, messageids
from docai.contracts.artifacts import DocumentsFile, DocumentSpan, LinesFile
from docai.contracts.llm import SegmentationVerdict
from docai.contracts.messages import Envelope, parse_payload
from docai.documents.artifactio import read_model, write_model
from docai.resources import prompts
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send


def _first_text(lf: LinesFile) -> str:
    return next((l.text.strip() for l in lf.lines if l.text.strip()), "")


def _page_x_of_y(text: str) -> tuple[int, int] | None:
    m = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", text, re.I)
    return (int(m[1]), int(m[2])) if m else None


def _ref(lf: LinesFile) -> str | None:
    for l in lf.lines:
        if m := re.match(r"^(?:Ref:|Contract No\.)\s*(\S+)", l.text.strip()):
            return m[1]
    return None


def cue(a: LinesFile, b: LinesFile) -> str | None:
    """'new', 'same', or None when the cues do not decide."""
    head = _first_text(b)
    if (n := _page_x_of_y(" ".join(l.text for l in b.lines))) and n[0] == 1:
        return "new"
    ra, rb = _ref(a), _ref(b)
    if ra and rb and ra != rb:
        return "new"
    if head and head.isupper() and len(head.split()) >= 2:
        return "new"  # a new title or letterhead at the top
    if re.match(r"^\d+\.\s", head) or head[:1].islower():
        return "same"  # numbered clause or a sentence that carries over
    return None


def handle(ctx: Context, env: Envelope) -> None:
    parse_payload(env)
    dossier_id, rev = revision_of(env)
    dept = keys.department_of(dossier_id)
    dkey = keys.dossier_key(dossier_id, rev)
    d = ctx.ops.get_dossier(dossier_id, rev)
    pages = ctx.ops.list_pages(dossier_id, rev)
    files = ctx.ops.list_files(dossier_id, rev)
    lfs = {p.page_no: read_model(ctx.blobs, "extracted", keys.PageRef(dossier_id, rev, p.page_no).dir + "lines.v1.json", LinesFile) for p in pages}
    by_no = {p.page_no: p for p in pages}

    spans: list[list[int]] = []
    for n in sorted(lfs):
        if not spans:
            spans.append([n]); continue
        a, b = lfs[n - 1], lfs[n]
        same_file = by_no[n - 1].source_file == by_no[n].source_file
        digital = {f.name for f in files if f.route == "digital"}
        if d.segmentation == "per_file" or by_no[n].source_file in digital or by_no[n - 1].source_file in digital:
            decision = "same" if same_file else "new"  # a converted file is one document, however long, and never merges with scans
        elif by_no[n].status == "failed" or by_no[n - 1].status == "failed":
            decision = "same"  # a placeholder takes part so page numbers stay aligned; the document is flagged has_gaps
        else:
            decision = cue(a, b)
            if decision is None:
                user = json.dumps({"A": [{"line_id": l.id, "text": l.text} for l in a.lines[-8:]],
                                   "B": [{"line_id": l.id, "text": l.text} for l in b.lines[:8]]}, ensure_ascii=False)
                v = ctx.chat.complete_json("segmentation", prompts.load("segmentation"), user, SegmentationVerdict)
                assert isinstance(v, SegmentationVerdict)
                decision = "new" if v.verdict == "new" else "same"  # 'unsure' keeps the pages together
        spans.append([n]) if decision == "new" else spans[-1].append(n)

    docs = []
    for seq, nums in enumerate(spans, start=1):
        docs.append(DocumentSpan(
            document_id=keys.document_id(dossier_id, rev, seq), first_page=nums[0], last_page=nums[-1],
            title=_first_text(lfs[nums[0]]).title(), cues="", source_files=sorted({by_no[n].source_file for n in nums}),
            has_gaps=any(by_no[n].status == "failed" for n in nums)))
    write_model(ctx.blobs, "extracted", f"{keys.extracted_dossier_dir(dossier_id, rev)}documents.json",
                DocumentsFile(dossier_key=dkey, segmentation=d.segmentation, documents=docs))  # type: ignore[arg-type]
    ctx.ops.register_documents(dossier_id, rev, [
        {"document_id": x.document_id, "seq": i, "first_page": x.first_page, "last_page": x.last_page, "title": x.title, "has_gaps": x.has_gaps}
        for i, x in enumerate(docs, start=1)])
    if d.pages_failed:
        send(ctx, envelope("dossier.partial", dkey, department=dept, dossier_id=dossier_id, revision=rev,
                           payload={"failed_pages": d.pages_failed}), message_id=f"partial:{dkey}")
    for x in docs:
        send(ctx, envelope("document.metadata.requested", x.document_id, department=dept, dossier_id=dossier_id, revision=rev,
                           payload={"document_id": x.document_id}), message_id=messageids.message_id("metadata", x.document_id))


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
