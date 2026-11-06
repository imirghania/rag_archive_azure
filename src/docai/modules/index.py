"""job-index: makes chunks searchable and keeps the index in step with access changes and flags (spec, Step 10; Workflow 6, 8)."""
from __future__ import annotations

import json

from docai.contracts import keys
from docai.contracts.artifacts import ChunkRecord
from docai.contracts.chunkfile import from_parquet
from docai.contracts.messages import ChunkFlagged, Envelope, IndexRequested, parse_payload
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send

BATCH = 1000


def to_index_doc(c: ChunkRecord) -> dict:
    d = c.model_dump(mode="json", by_alias=False)
    d.pop("schema_", None)
    text = d.pop("text")
    d["text_ar" if c.language == "ar" else "text_en"] = text
    d["trust_tiers_json"] = json.dumps(d.pop("trust_tiers"), ensure_ascii=False)
    return d


def handle(ctx: Context, env: Envelope) -> None:
    if env.type == "document.index.requested":
        _index(ctx, env)
    elif env.type == "document.acl.changed":
        _acl(ctx, env)
    elif env.type == "chunk.flagged":
        _flag(ctx, env)
    else:
        raise ValueError(f"job-index does not handle {env.type}")


def _index(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, IndexRequested)
    dossier_id, rev = revision_of(env)
    doc = ctx.ops.get_document(req.document_id)
    if req.version < doc.current_version:
        return  # a newer version exists: this message is stale and the index must not go backwards
    chunks = from_parquet(ctx.blobs.read("curated", req.parquet))
    acl = ctx.ops.dossier_acl(dossier_id)  # always read from SQL, never from the file: a restriction may have changed since
    docs = []
    for c in chunks:
        c.acl_groups = acl
        docs.append(to_index_doc(c))
    for i in range(0, len(docs), BATCH):
        ctx.search.upload("docs", docs[i:i + BATCH])  # mergeOrUpload: chunk IDs carry the version, so v1 never overwrites v2
    new_ids = {c.chunk_id for c in chunks}
    old = [i for i in ctx.search.ids("docs", document_id=req.document_id, version_lt=req.version) if i not in new_ids]
    ctx.search.delete("docs", old)  # only after the new chunks are confirmed: the document is never missing from search
    ctx.ops.mark_indexed(req.document_id, req.version)
    send(ctx, envelope("document.indexed", req.document_id, department=env.department, dossier_id=dossier_id, revision=rev,
                       payload={"version": req.version}), message_id=f"indexed:{req.document_id}:v{req.version}")
    if ctx.ops.try_complete_dossier(dossier_id, rev) == "completed" and rev > 1:
        _swap(ctx, dossier_id, rev)  # a newer revision is searchable: the older one goes (a `partial` revision never swaps itself)


def _swap(ctx: Context, dossier_id: str, rev: int) -> None:
    for doc_id in ctx.ops.supersede_older_revisions(dossier_id, rev):  # idempotent: a repeat returns nothing
        ctx.search.delete("docs", ctx.search.ids("docs", document_id=doc_id))
        send(ctx, envelope("document.removed", doc_id, department=keys.department_of(dossier_id), dossier_id=dossier_id, revision=rev,
                           payload={"superseded_by_revision": rev}), message_id=f"removed:{doc_id}")


def _acl(ctx: Context, env: Envelope) -> None:
    dossier_id, _ = revision_of(env)
    acl = ctx.ops.dossier_acl(dossier_id)
    for cid in ctx.search.ids("docs", document_id=env.subject):
        ctx.search.merge("docs", {"chunk_id": cid, "acl_groups": acl})  # a missing chunk is "not loaded yet", not an error


def _flag(ctx: Context, env: Envelope) -> None:
    p = parse_payload(env)
    assert isinstance(p, ChunkFlagged)
    ctx.search.merge("docs", {"chunk_id": p.chunk_id, "injection_suspect": p.injection_suspect, "flag_source": p.flag_source,
                              "flagged_at": ctx.clock.now().isoformat()})
    if p.injection_suspect:  # puts the chunk on the steward's "Flagged content" tab
        doc_id, _, _ = keys.parse_chunk_id(p.chunk_id)
        ctx.ops.upsert_content_flag(p.chunk_id, doc_id, env.department, p.flag_source)


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
