"""app-hint-worker: acts on hint state changes (spec, Workflow 5). It always re-reads the hint and acts on its current
state, never on the sequence of messages; a message whose row_version is behind is stale and is completed without action."""
from __future__ import annotations

import math
from datetime import datetime

from docai.contracts import keys
from docai.contracts.artifacts import NoteRecord
from docai.contracts.enums import HintStatus, HintType, TaskReason
from docai.contracts.messages import Envelope, HintChanged, parse_payload
from docai.resources import searchdefs
from docai.runtime.context import Context
from docai.runtime.hintacl import hint_audience
from docai.runtime.messaging import envelope, send

_NEAR_DUPLICATE = 0.9


def handle(ctx: Context, env: Envelope) -> None:
    if env.type == "dossier.acl.changed":
        return _acl_changed(ctx, env)
    msg = parse_payload(env)
    assert isinstance(msg, HintChanged)
    h = ctx.ops.get_hint(env.subject)
    if h["row_version"] != msg.row_version:
        return  # the hint was changed after this message was sent
    {"submitted": _submitted, "approved": _approved, "rejected": _rejected, "revoked": _revoked, "published": _published}.get(h["status"], lambda *_: None)(ctx, h)


def _event(ctx: Context, kind: str, h: dict, message_id: str, **payload) -> None:
    send(ctx, envelope(kind, h["hint_id"], department=h["department"],
                       payload={"hint_id": h["hint_id"], "author_oid": h["author_oid"], "text": h["text"][:120], **payload}), message_id=message_id)


def _cosine(a: list[float], b: list[float]) -> float:
    n = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / n if n else 0.0


def _submitted(ctx: Context, h: dict) -> None:
    if h["type"] == HintType.transcription_fix:
        # a misread line goes to a reviewer, pre-filled with the suggestion; a different expert or a steward settles it
        ref = keys.LineRef.parse(h["target_line_key"])
        ctx.ops.create_review_task(department=h["department"], dossier_id=ref.page.dossier_id, revision=ref.page.revision, page_no=ref.page.page_no,
                                   line_id=ref.line_id, line_key=ref.key, reason=TaskReason.expert_hint.value, suggested_text=h["suggested_text"], hint_id=h["hint_id"])
        return
    checks: dict = {"prompt_shields": ctx.safety.shield(documents=[h["text"]]).document_attacks[0], "similar": []}
    vec = ctx.embedder.embed([h["text"]])[0]
    scope = sorted(g for g, (dept, _) in ctx.ops.registered_groups().items() if dept == h["department"])
    for hit in ctx.search.search("notes", text=h["text"], vector=vec, acl_groups=scope, top=3):
        sim = _cosine(vec, hit.doc.get("text_vector") or [])
        if sim >= _NEAR_DUPLICATE:
            checks["similar"].append({"hint_id": hit.id, "similarity": round(sim, 2)})
    ctx.ops.set_hint_status(h["hint_id"], HintStatus.awaiting_approval.value, h["row_version"], check_results=checks)


def _published(ctx: Context, h: dict) -> None:
    if h["type"] == HintType.transcription_fix:  # its outcome was recorded by the reviewer; tell the author
        _event(ctx, "hint.published", h, f"published:{h['hint_id']}:v{h['version']}", approved_by=h.get("approved_by_name") or "a reviewer", reason="transcription_fix")


def _note(ctx: Context, h: dict, acl: list[str]) -> dict:
    ev = h["evidence"] or []
    rec = NoteRecord(hint_id=h["hint_id"], hint_type=h["type"], department=h["department"], text=h["text"], acl_groups=acl,
                     scope_dossier_ids=h["scope_dossier_ids"], evidence_chunk_ids=[e["chunk_id"] for e in ev], evidence_status=h["evidence_status"],
                     author=h["author_name"], approved_by=h.get("approved_by_name") or "", review_by=h.get("review_by"),
                     approved_at=datetime.fromisoformat(h["approved_at"]) if h.get("approved_at") else None, text_vector=ctx.embedder.embed([h["text"]])[0])
    d = rec.model_dump(mode="json", by_alias=False)
    d.pop("schema_", None)
    d["text_ar" if h["language"] == "ar" else "text_en"] = d.pop("text")
    d["language"] = h["language"]
    return d


def _approved(ctx: Context, h: dict) -> None:
    acl = h["acl_groups"] or hint_audience(ctx, h)  # a steward's reasoned "Widen" is already stored on the hint
    if h["type"] == HintType.context_note:
        ctx.search.upload("notes", [_note(ctx, h, acl)])
        ctx.ops.record_publication(h["hint_id"], "notes_index", "upsert")
    elif h["type"] == HintType.terminology:
        _rebuild_synonyms(ctx, h)
        ctx.ops.record_publication(h["hint_id"], "synonyms_en", "upsert")
        ctx.ops.record_publication(h["hint_id"], "synonyms_ar", "upsert")
    _event(ctx, "hint.published", h, f"published:{h['hint_id']}:v{h['version']}", approved_by=h.get("approved_by_name"), reason="approval")
    ctx.ops.set_hint_status(h["hint_id"], HintStatus.published.value, h["row_version"], acl_groups=acl)  # last: a retry redoes everything above harmlessly


def _rebuild_synonyms(ctx: Context, extra: dict | None = None) -> None:
    """Replaces each map whole, from the seed rules and every published terminology hint (plus `extra`, which is about to be
    published). The next query uses the new rules, without reindexing."""
    base = {m["name"]: [r for r in m["synonyms"].split("\n") if r] for m in searchdefs.synonym_maps()}
    hints = [x for x in ctx.ops.list_hints(status="published", type=HintType.terminology.value) if not extra or x["hint_id"] != extra["hint_id"]]
    hints += [extra] if extra else []
    for x in hints:
        for name in base:
            base[name].append(", ".join(x["terms"] or []))
    for name, rules in base.items():
        ctx.search.put_synonym_map(name, rules)


def _rejected(ctx: Context, h: dict) -> None:
    _event(ctx, "hint.rejected", h, f"rejected:{h['hint_id']}:v{h['version']}", reason=h.get("decision_reason") or "")


def _revoked(ctx: Context, h: dict) -> None:
    if h["type"] == HintType.context_note:
        ctx.search.delete("notes", [h["hint_id"]])
        ctx.ops.record_publication(h["hint_id"], "notes_index", "delete", "revoke")
    elif h["type"] == HintType.terminology:
        _rebuild_synonyms(ctx)  # the hint is no longer `published`, so its rule is gone
        ctx.ops.record_publication(h["hint_id"], "synonyms_en", "delete", "revoke")
    _event(ctx, "hint.revoked", h, f"revoked:{h['hint_id']}:v{h['version']}", reason=h.get("decision_reason") or "")


def _acl_changed(ctx: Context, env: Envelope) -> None:
    """A note anchored to a restricted dossier must follow the restriction, or it would leak what was just restricted."""
    v = int(env.payload.get("acl_version", 0))
    for h in ctx.ops.hints_anchored_to(env.subject):
        acl = hint_audience(ctx, h)
        if h["type"] == HintType.context_note and ctx.search.merge("notes", {"hint_id": h["hint_id"], "acl_groups": acl}):
            ctx.ops.record_publication(h["hint_id"], "notes_index", "acl_update", "acl_change")
        _event(ctx, "hint.published", h, f"published:{h['hint_id']}:acl{v}", reason="acl_change", approved_by=h.get("approved_by_name"))


if __name__ == "__main__":
    from docai.runtime.launch import queue_consumer

    queue_consumer(handle)
