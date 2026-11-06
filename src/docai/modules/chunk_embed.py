"""job-chunk-embed: cuts a document into chunks, labels and embeds them (spec, Workflow 1, Step 9)."""
from __future__ import annotations

import re

from docai.contracts import keys, messageids
from docai.contracts.artifacts import ChunkRecord, Line, LinesFile, Metadata
from docai.contracts.chunkfile import to_parquet
from docai.contracts.enums import TrustTier, min_tier
from docai.contracts.messages import ChunkRequested, Envelope, parse_payload
from docai.documents.artifactio import read_model
from docai.documents.linetext import mark_disagreement
from docai.documents.pagefiles import document_lines
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send

_ARABIC = re.compile(r"[؀-ۿ]")


def approx_tokens(text: str) -> int:
    return round(len(text.split()) * 1.3) + (len(_ARABIC.findall(text)) // 6)


def _line_text(ln: Line) -> str:
    return mark_disagreement(ln.candidates) if ln.tier is TrustTier.unverified and ln.candidates else ln.text


def blocks(pages: list[tuple[int, LinesFile]]) -> list[list[tuple[int, Line]]]:
    """Paragraph blocks in reading order. A margin note stays in the block of the paragraph it is anchored to."""
    out: list[list[tuple[int, Line]]] = []
    for n, lf in pages:
        main = [l for l in lf.lines if l.placement == "main" and l.text.strip()]
        notes = [l for l in lf.lines if l.placement != "main"]
        paras: dict[str, list[Line]] = {}
        for l in main:
            paras.setdefault(l.paragraph or f"_{l.id}", []).append(l)
        used: set[str] = set()
        for pid, ls in paras.items():
            blk = [(n, l) for l in ls] + [(n, x) for x in notes if x.anchor == pid]
            used |= {x.id for x in notes if x.anchor == pid}
            out.append(blk)
        for x in notes:
            if x.id not in used:
                out.append([(n, x)])  # a page note with no paragraph
    return out


def make_chunks(doc_id: str, version: int, pages: list[tuple[int, LinesFile]], max_tokens: int) -> list[dict]:
    chunks, cur, cur_tokens = [], [], 0
    for blk in blocks(pages):
        text = " ".join(_line_text(l) for _, l in blk)
        t = approx_tokens(text)
        if cur and cur_tokens + t > max_tokens:
            chunks.append(cur); cur, cur_tokens = [], 0
        cur.extend(blk); cur_tokens += t
    if cur:
        chunks.append(cur)
    result = []
    for i, blk in enumerate(chunks):
        refs = [f"p{n:03d}/{l.id}" for n, l in blk]
        result.append({
            "n": i, "text": "\n".join(_line_text(l) for _, l in blk), "pages": sorted({n for n, _ in blk}), "line_refs": refs,
            "trust_tiers": {f"p{n:03d}/{l.id}": l.tier for n, l in blk}, "min_trust": min_tier([l.tier for _, l in blk])})
    return result


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, ChunkRequested)
    dossier_id, rev = revision_of(env)
    dept = keys.department_of(dossier_id)
    doc = ctx.ops.get_document(req.document_id)
    pages = document_lines(ctx.blobs, dossier_id, rev, doc.first_page, doc.last_page, upto_version=req.version)
    meta = read_model(ctx.blobs, "extracted", keys.extracted_document_dir(req.document_id) + "metadata.json", Metadata)
    acl = ctx.ops.dossier_acl(dossier_id)

    pieces = make_chunks(req.document_id, req.version, pages, ctx.settings.tuning.chunk_max_tokens)
    # Screen every new chunk for planted instructions before it can be searched (spec: Prompt Shields document check)
    verdict = ctx.safety.shield(documents=[p["text"] for p in pieces])
    vectors = ctx.embedder.embed([p["text"] for p in pieces])
    records = []
    for p, vec, attack in zip(pieces, vectors, verdict.document_attacks, strict=True):
        records.append(ChunkRecord(
            chunk_id=keys.chunk_id(req.document_id, req.version, p["n"]), document_id=req.document_id, dossier_id=dossier_id,
            revision=rev, version=req.version, department=dept, text=p["text"], pages=p["pages"], line_refs=p["line_refs"],
            trust_tiers=p["trust_tiers"], min_trust=p["min_trust"], min_trust_rank=p["min_trust"].rank, acl_groups=acl,
            doc_type=meta.doc_type.value if meta.doc_type else None, doc_date=meta.date.value if meta.date else None,
            reference=meta.reference.value if meta.reference else None, subject=meta.subject.value if meta.subject else None,
            language="ar" if len(_ARABIC.findall(p["text"])) > len(p["text"]) / 3 else "en", injection_suspect=attack, text_vector=vec))
    path = keys.chunks_parquet_path(req.document_id, req.version)
    ctx.blobs.write("curated", path, to_parquet(records), overwrite=True)  # vectors stay here: a rebuild never pays for embeddings again
    send(ctx, envelope("document.index.requested", 
                    req.document_id, department=dept, dossier_id=dossier_id, revision=rev,
                    payload={"document_id": req.document_id, "version": req.version, "parquet": path}),
        message_id=messageids.message_id("index", req.document_id, version=req.version), document_id=req.document_id)


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
