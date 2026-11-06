"""job-metadata: catalogue fields of each document, every value tied to a quotable line (spec, Step 8)."""
from __future__ import annotations

import re

from docai.contracts import keys, messageids
from docai.contracts.artifacts import Catalog, Evidenced, Metadata
from docai.contracts.enums import TrustTier, min_tier
from docai.contracts.llm import MetadataOutput
from docai.contracts.messages import Envelope, MetadataRequested, parse_payload
from docai.documents.artifactio import write_model
from docai.documents.pagefiles import document_lines
from docai.resources import prompts
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send

_DOSSIER_PARTS = re.compile(r"^(?:[A-Z]{2,3})-(C\d{2})-(S\d)-(F\d{4})$")


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, MetadataRequested)
    dossier_id, rev = revision_of(env)
    dept = keys.department_of(dossier_id)
    doc = ctx.ops.get_document(req.document_id)
    pages = document_lines(ctx.blobs, dossier_id, rev, doc.first_page, doc.last_page)

    labelled, tiers, all_text = [], [], {}
    for n, lf in pages:
        for ln in lf.lines:
            key = f"p{n:03d}/{ln.id}"
            labelled.append(f"{key}: {ln.text}")
            all_text[key] = ln.text
            tiers.append(ln.tier)
    out = ctx.chat.complete_json("metadata", prompts.load("metadata"), "\n".join(labelled), MetadataOutput)
    assert isinstance(out, MetadataOutput)

    def keep(e: Evidenced | None) -> Evidenced | None:
        # a value without a quotable line is dropped
        return e if e and e.evidence in all_text and e.value.strip() else None

    parts = _DOSSIER_PARTS.match(dossier_id)
    meta = Metadata(document_id=req.document_id,
                    catalog=Catalog(department=dept, cabinet=parts[1] if parts else None, shelf=parts[2] if parts else None,
                                    section=parts[3] if parts else None),
                    doc_type=keep(out.doc_type), date=keep(out.date), reference=keep(out.reference), subject=keep(out.subject),
                    languages=list(out.languages), min_trust=min_tier(tiers) if tiers else TrustTier.missing, has_gaps=doc.has_gaps)
    write_model(ctx.blobs, "extracted", keys.extracted_document_dir(req.document_id) + "metadata.json", meta)
    ctx.ops.set_document_metadata(req.document_id, {
        "doc_type": meta.doc_type.value if meta.doc_type else None, "doc_date": meta.date.value if meta.date else None,
        "reference": meta.reference.value if meta.reference else None, "subject": meta.subject.value if meta.subject else None,
        "languages": meta.languages, "min_trust": meta.min_trust.value})
    send(ctx, envelope("document.chunk.requested", req.document_id, department=dept, dossier_id=dossier_id, revision=rev,
                       payload={"document_id": req.document_id, "version": doc.current_version}),
         message_id=messageids.message_id("chunk", req.document_id, version=doc.current_version), document_id=req.document_id)


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
