"""app-retrieval: the search tools of the agent. It adds the security filter itself, from the scope the caller passes,
and the model never sees or sets that scope (spec, Workflow 6, Step 7)."""
from __future__ import annotations

from typing import Any

from fastapi import Depends
from pydantic import BaseModel

from docai.security.access import Principal, access_scope
from docai.runtime.context import Context
from docai.runtime.http import make_principal_dep, new_app

LINE_FIELDS = ("chunk_id", "document_id", "dossier_id", "version", "department", "pages", "line_refs", "trust_tiers_json", "min_trust",
               "doc_type", "doc_date", "reference", "subject", "language", "acl_groups")


def _lines(doc: dict[str, Any]) -> list[dict[str, str]]:
    """One entry per line, aligned with `line_refs`: the chunk text has one line of text per reference."""
    texts = (doc.get("text_en") or doc.get("text_ar") or "").split("\n")
    refs = doc.get("line_refs", [])
    return [{"ref": r, "text": texts[i] if i < len(texts) else ""} for i, r in enumerate(refs)]


def search_documents(ctx: Context, *, scope: list[str], query: str, language: str = "en", top: int = 8, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not scope or not query.strip():
        return []
    allowed = {k: v for k, v in (filters or {}).items() if k in ("doc_type", "reference", "dossier_id") and v}
    vec = ctx.embedder.embed([query])[0]
    out = []
    for h in ctx.search.search("docs", text=query, vector=vec, acl_groups=scope, top=top or ctx.settings.tuning.search_top, filters=allowed):
        out.append({**{k: h.doc.get(k) for k in LINE_FIELDS}, "lines": _lines(h.doc), "score": round(h.score, 4)})
    return out


def search_notes(ctx: Context, *, scope: list[str], query: str, top: int = 5) -> list[dict[str, Any]]:
    if not scope or not query.strip():
        return []
    vec = ctx.embedder.embed([query])[0]
    return [{"hint_id": h.doc["hint_id"], "text": h.doc.get("text_en") or h.doc.get("text_ar"), "approved_by": h.doc.get("approved_by"),
             "approved_at": h.doc.get("approved_at"), "evidence_status": h.doc.get("evidence_status"), "score": round(h.score, 4)}
            for h in ctx.search.search("notes", text=query, vector=vec, acl_groups=scope, top=top)]


class DocQuery(BaseModel):
    query: str
    language: str = "en"
    top: int = 8
    filters: dict[str, Any] | None = None


class NoteQuery(BaseModel):
    query: str
    top: int = 5


def create_app(ctx: Context):
    """The scope is worked out here from the caller's own token. A body field could be forged by a compromised caller; the
    token cannot, and the model never sees either."""
    app, principal = new_app("app-retrieval"), make_principal_dep(ctx)

    def scope_of(p: Principal) -> list[str]:
        return access_scope(ctx.ops.registered_groups(), p.groups)

    @app.post("/search/documents")
    def docs(q: DocQuery, p: Principal = Depends(principal)):
        return search_documents(ctx, scope=scope_of(p), query=q.query, language=q.language, top=q.top, filters=q.filters)

    @app.post("/search/notes")
    def notes(q: NoteQuery, p: Principal = Depends(principal)):
        return search_notes(ctx, scope=scope_of(p), query=q.query, top=q.top)

    return app


if __name__ == "__main__":
    from docai.runtime.launch import http_app

    http_app(create_app)
