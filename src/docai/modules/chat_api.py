"""app-chat-api, service layer: conducts one answer (spec, Workflow 6).

The model never sees or sets the user's permissions. The agent asks for searches; this code runs them with the access
scope worked out from the validated token. `scope` below is always the output of docai.security.access.access_scope."""
from __future__ import annotations

import io
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.responses import Response
from PIL import Image
from pydantic import BaseModel

from docai.contracts import keys
from docai.contracts.artifacts import LinesFile
from docai.contracts.enums import Capability, EvidenceStatus, HintType, TrustTier
from docai.contracts.llm import RouterOutput
from docai.documents.artifactio import read_model
from docai.ports import ToolCall, Verdict
from docai.resources import prompts
from docai.runtime.context import Context
from docai.runtime.http import make_principal_dep, new_app
from docai.runtime.messaging import envelope, send
from docai.security.access import Principal, access_scope, departments_with, require, scope_hash
from docai.security.tokens import bearer_token, current_token

log = logging.getLogger("docai.security")
_TOKEN = re.compile(r"[a-z0-9؀-ۿ]+")
_STOP = {"the", "for", "was", "and", "how", "much", "what", "did", "who", "are", "not", "with"}

MESSAGES = {
    "en": {
        "no_evidence": "I could not find supporting evidence for this in the documents you have access to. If you are a domain expert, you can add a hint under this answer.",
        "unverified": "A handwritten note on this subject exists, but its content is still awaiting expert verification, so I cannot state it yet.",
        "out_of_scope": "I answer questions about the documents in the archive: letters, contracts, memos and similar. I cannot help with that request.",
        "unsafe": "I could not process this question.",
        "partial_tail": "Part of the answer could not be verified against the documents and was left out.",
    },
    "ar": {
        "no_evidence": "لم أجد أدلة داعمة لهذا في المستندات المتاحة لك. إذا كنت خبيراً في المجال فيمكنك إضافة تلميح تحت هذه الإجابة.",
        "unverified": "توجد ملاحظة مكتوبة بخط اليد حول هذا الموضوع، لكن محتواها ما زال بانتظار تحقق أحد الخبراء، لذلك لا أستطيع ذكره الآن.",
        "out_of_scope": "أجيب عن الأسئلة المتعلقة بمستندات الأرشيف: الرسائل والعقود والمذكرات وما شابهها. لا يمكنني المساعدة في هذا الطلب.",
        "unsafe": "تعذّرت معالجة هذا السؤال.",
        "partial_tail": "تعذّر التحقق من جزء من الإجابة مقابل المستندات وتم حذفه.",
    },
}


@dataclass
class Citation:
    chunk_id: str
    ref: str
    text: str
    document_id: str
    line_key: str


@dataclass
class Answer:
    answer_id: str
    conversation_id: str
    text: str
    language: str
    intent: str
    abstained: bool = False
    reason: str | None = None
    citations: list[Citation] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)  # line keys: the user can open them in the review queue's demand


def _tiers(doc: dict[str, Any]) -> dict[str, TrustTier]:
    return {k: TrustTier(v) for k, v in json.loads(doc.get("trust_tiers_json") or "{}").items()}


def _noncitable_lines(evidence: dict[str, dict[str, Any]]) -> list[tuple[str, str, str]]:
    """(chunk_id, ref, text) of every shown line whose tier is not citable: the only lines that can have a review task."""
    out = []
    for cid, doc in evidence.items():
        tiers = _tiers(doc)
        for ln in doc["lines"]:
            if not tiers.get(ln["ref"], TrustTier.unverified).citable:
                out.append((cid, ln["ref"], ln["text"]))
    return out


def answer(ctx: Context, *, user_oid: str, scope: list[str], question: str, conversation_id: str | None = None) -> Answer:
    t0 = time.monotonic()
    conv = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    aid = f"ans-{uuid.uuid4().hex[:6]}"
    evidence: dict[str, dict[str, Any]] = {}
    state: dict[str, Any] = {"language": "en", "intent": "doc_lookup", "verdict": None}

    def finish(text: str, *, abstained=False, reason=None, citations=None, needs_review=None) -> Answer:
        a = Answer(aid, conv, text, state["language"], state["intent"], abstained, reason, citations or [], needs_review or [])
        _record_demand(ctx, aid, evidence, state.get("blocked", []), question, abstained or bool(needs_review))
        ctx.ops.save_turn(answer_id=aid, conversation_id=conv, user_oid=user_oid, question=question, answer=text, abstained=abstained,
                        abstain_reason=reason, intent=state["intent"], language=state["language"],
                        evidence=[{"chunk_id": c, "lines": [x["ref"] for x in d["lines"]]} for c, d in evidence.items()],
                        verdict=None if state["verdict"] is None else {"claims": [c.__dict__ for c in state["verdict"].claims]},
                          scope_hash=scope_hash(scope), latency_ms=int((time.monotonic() - t0) * 1000))
        return a

    # 3. safety screen on the question
    if ctx.safety.shield(question=question).question_attack:
        return finish(MESSAGES["en"]["unsafe"], abstained=True, reason="unsafe_question")

    # 5. router
    history = ctx.ops.history(conv, user_oid, 3)
    routed = ctx.chat.complete_json("router", prompts.load("router"), json.dumps(
        {"question": question, "history": [{"q": h["question"], "a": h["answer"]} for h in history], "glossary": ""}, ensure_ascii=False), RouterOutput)
    assert isinstance(routed, RouterOutput)
    state.update(language=routed.language, intent=routed.intent)
    msg = MESSAGES[routed.language]
    if routed.intent == "out_of_scope":
        return finish(msg["out_of_scope"], abstained=True, reason="out_of_scope")

    # 6-7. the agent asks for tools; they run with the caller's scope, and planted instructions are dropped
    def tool(call: ToolCall) -> str:
        if call.name == "search_notes":
            return json.dumps(ctx.retrieval.search_notes(scope=scope, query=call.arguments.get("query", ""), top=int(call.arguments.get("top", 5))), ensure_ascii=False)
        if call.name != "search_documents":
            return json.dumps({"error": f"unknown tool {call.name}"})
        results = ctx.retrieval.search_documents(scope=scope, query=call.arguments.get("query", ""), language=call.arguments.get("language", routed.language),
                                                top=int(call.arguments.get("top", ctx.settings.tuning.search_top)), filters=routed.filters.model_dump())
        shield = ctx.safety.shield(documents=["\n".join(x["text"] for x in r["lines"]) for r in results])
        kept = []
        for r, attack in zip(results, shield.document_attacks, strict=True):
            if attack:  # removed before the model sees it, excluded for everyone, and left for a steward to judge
                log.warning("security event: planted instruction", extra={"chunk_id": r["chunk_id"], "question_hash": scope_hash([question])})
                doc_id = r["document_id"]
                send(ctx, envelope("chunk.flagged", doc_id, department=r["department"], dossier_id=r["dossier_id"],
                                payload={"chunk_id": r["chunk_id"], "injection_suspect": True}),
                    message_id=f"flag:{r['chunk_id']}", document_id=doc_id)
                state["flagged_dropped"] = True
                continue
            evidence[r["chunk_id"]] = r
            kept.append({k: r[k] for k in ("chunk_id", "document_id", "reference", "doc_date", "subject", "doc_type", "lines")})
        return json.dumps(kept, ensure_ascii=False)

    queries = {"en": routed.query_en, "ar": routed.query_ar}
    draft = ctx.agent.run(question=question, queries=queries, history=history, tools=tool)

    if draft.startswith("NO_EVIDENCE"):
        state["blocked"] = []
        reason = "flagged_content" if state.get("flagged_dropped") else "no_evidence"
        return finish(msg["no_evidence"], abstained=True, reason=reason)

    # 9. verification, with one corrected draft allowed
    verdict = ctx.verifier.verify(draft=draft, evidence=evidence, scope=scope)
    if not verdict.ok:
        failed = next(c for c in verdict.claims if c.verdict != "supported")
        draft2 = ctx.agent.run(question=question, queries=queries, history=history, tools=tool,
                            correction=f"Claim {failed.claim_id} failed verification ({failed.failed_layer}: {failed.detail}). Correct it or leave it out.")
        if not draft2.startswith("NO_EVIDENCE"):
            second = ctx.verifier.verify(draft=draft2, evidence=evidence, scope=scope)
            verdict = Verdict(second.claims, sorted(set(verdict.blocked_lines) | set(second.blocked_lines)))
    state["verdict"], state["blocked"] = verdict, verdict.blocked_lines

    supported = verdict.supported
    if not supported:
        reason = "unverified" if verdict.blocked_lines else "unsupported"
        return finish(msg["unverified"] if verdict.blocked_lines else msg["no_evidence"], abstained=True, reason=reason, needs_review=verdict.blocked_lines)
    text = " ".join(c.text.rstrip(".") + "." for c in supported)
    cites: list[Citation] = []
    for c in supported:
        for ref in c.citations:
            cid, line_ref = ref.split("#")
            ln = next(x for x in evidence[cid]["lines"] if x["ref"] == line_ref)
            cites.append(Citation(cid, line_ref, ln["text"], evidence[cid]["document_id"], keys.line_key_of_chunk(cid, line_ref)))
    if verdict.blocked_lines:
        text += " " + msg["unverified"]
    elif len(supported) < len(verdict.claims):
        text += " " + msg["partial_tail"]
    return finish(text, citations=cites, needs_review=verdict.blocked_lines)


def _record_demand(ctx: Context, answer_id: str, evidence: dict[str, dict[str, Any]], blocked: list[str], question: str, refused: bool) -> None:
    """Every shown line that is not citable counts as *retrieved*; lines that made the verifier refuse a claim, or that
    probably decided an abstention, count as *blocked*. These counts order the review queue (Workflow 4)."""
    hits = [{"line_key": keys.line_key_of_chunk(c, ref), "kind": "retrieved"} for c, ref, _ in _noncitable_lines(evidence)]
    hits += [{"line_key": b, "kind": "blocked"} for b in blocked]
    if refused and not blocked:
        q = set(_TOKEN.findall(question.lower())) - _STOP
        hits += [{"line_key": keys.line_key_of_chunk(c, ref), "kind": "blocked"} for c, ref, text in _noncitable_lines(evidence)
                if len(q & set(_TOKEN.findall(text.lower()))) >= 1]
    if hits:
        ctx.ops.record_demand(hits, answer_id)


# hints (expert side)
class HintError(Exception):
    pass


def suggest_evidence(ctx: Context, p: Principal, text: str, top: int = 3) -> list[dict[str, Any]]:
    """As the expert types, search with the hint's own text under the expert's scope. A hint uses the documents' vocabulary
    ("Jebel Ali", "4410"), which the failed question did not, so this search often finds the bridge."""
    scope = access_scope(ctx.ops.registered_groups(), p.groups)
    return [{"chunk_id": r["chunk_id"], "lines": r["lines"][:3], "reference": r["reference"], "subject": r["subject"]}
            for r in ctx.retrieval.search_documents(scope=scope, query=text, top=top)]


def submit_hint(ctx: Context, p: Principal, *, department: str, type: HintType, language: str, text: str, terms: list[str] | None = None,
                evidence: list[dict[str, Any]] | None = None, scope_dossier_ids: list[str] | None = None, from_answer: str | None = None,
                target_line_key: str | None = None, suggested_text: str | None = None) -> str:
    """Author and department come from the validated token, never from the request body. The server validates the evidence."""
    registry = ctx.ops.registered_groups()
    require(registry, p, Capability.review, department)
    scope = set(access_scope(registry, p.groups))
    if not text.strip():
        raise HintError("a hint needs text")
    if type is HintType.terminology and len(terms or []) < 2:
        raise HintError("a terminology hint lists at least two terms")
    checked = []
    for ev in evidence or []:  # each cited chunk must exist and be inside the author's scope; the quote is taken from the chunk
        doc = ctx.search.get("docs", ev["chunk_id"])
        if doc is None or not scope & set(doc.get("acl_groups", [])):
            raise HintError(f"evidence {ev['chunk_id']} was not found in your scope")
        refs = {x["ref"]: x["text"] for x in _lines_of(doc)}
        bad = [ln for ln in ev.get("lines", []) if ln not in refs]
        if bad:
            raise HintError(f"line {bad[0]} is not in {ev['chunk_id']}")
        checked.append({"chunk_id": ev["chunk_id"], "lines": ev.get("lines", []), "quote": " ".join(refs[ln] for ln in ev.get("lines", []))[:300],
                        "selected_by": "author"})
    if type is HintType.transcription_fix:
        ref = keys.LineRef.parse(target_line_key or "")
        if keys.department_of(ref.page.dossier_id) != department or not scope & set(ctx.ops.dossier_acl(ref.page.dossier_id)):
            raise HintError("the line is not in a dossier you may read")
        if not (suggested_text or "").strip():
            raise HintError("a transcription fix needs the suggested text")
    return ctx.ops.submit_hint(department=department, type=type.value, language=language, text=text.strip(), author_oid=p.oid, author_name=p.name,
                            terms=terms, scope_dossier_ids=scope_dossier_ids or [], evidence=checked,
                            evidence_status=(EvidenceStatus.documentary if checked else EvidenceStatus.tacit).value, from_answer=from_answer,
                            target_line_key=target_line_key, suggested_text=suggested_text)


def _lines_of(doc: dict[str, Any]) -> list[dict[str, str]]:
    texts = (doc.get("text_en") or doc.get("text_ar") or "").split("\n")
    return [{"ref": r, "text": texts[i] if i < len(texts) else ""} for i, r in enumerate(doc.get("line_refs", []))]


def citation_crop(ctx: Context, scope: list[str], chunk_id: str, ref: str) -> bytes:
    """The picture of the cited line. The chunk must be in the caller's scope; the browser never gets a storage address."""
    doc = ctx.search.get("docs", chunk_id)
    if doc is None or not set(scope) & set(doc.get("acl_groups", [])) or ref not in doc.get("line_refs", []):
        raise KeyError("citation")  # the same answer for a missing chunk and for one the caller may not see
    page_no, line_id = int(ref.split("/")[0][1:]), ref.split("/")[1]
    pref = keys.PageRef(doc["dossier_id"], doc["revision"], page_no)
    crop = f"{pref.dir}crops/{line_id}.png"
    if ctx.blobs.exists("extracted", crop):  # handwritten lines have a stored crop
        return ctx.blobs.read("extracted", crop)
    lf = read_model(ctx.blobs, "extracted", pref.dir + "lines.v1.json", LinesFile)  # printed lines are cut on demand
    box = lf.line(line_id).box
    m = round(box.height * ctx.settings.tuning.crop_margin_ratio)
    page = Image.open(io.BytesIO(ctx.blobs.read("extracted", pref.dir + "page.png")))
    out = io.BytesIO()
    page.crop((max(0, box.x0 - m), max(0, box.y0 - m), min(page.width, box.x1 + m), min(page.height, box.y1 + m))).save(out, "PNG")
    return out.getvalue()


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class HintRequest(BaseModel):
    department: str
    type: HintType
    language: str = "en"
    text: str
    terms: list[str] | None = None
    evidence: list[dict] | None = None
    scope_dossier_ids: list[str] | None = None
    from_answer: str | None = None
    target_line_key: str | None = None
    suggested_text: str | None = None


class FeedbackRequest(BaseModel):
    answer_id: str
    rating: int
    comment: str | None = None


def create_app(ctx: Context):
    app, principal = new_app("app-chat-api"), make_principal_dep(ctx)

    def scope_of(p: Principal) -> list[str]:
        return access_scope(ctx.ops.registered_groups(), p.groups)

    @app.post("/api/chat")
    def chat(req: ChatRequest, p: Principal = Depends(principal), token: str = Depends(bearer_token)):
        current_token.set(token)  # forwarded to app-retrieval and app-verifier, which work out the scope themselves
        if not departments_with(ctx.ops.registered_groups(), p, Capability.ask):
            raise PermissionError("you have no reader access to any department")
        a = answer(ctx, user_oid=p.oid, scope=scope_of(p), question=req.question, conversation_id=req.conversation_id)
        return {"answer_id": a.answer_id, "conversation_id": a.conversation_id, "text": a.text, "language": a.language, "intent": a.intent,
                "abstained": a.abstained, "reason": a.reason, "citations": [c.__dict__ for c in a.citations]}

    @app.get("/api/citations/{chunk_id}/crop")
    def crop(chunk_id: str, line: str, p: Principal = Depends(principal)):
        return Response(citation_crop(ctx, scope_of(p), chunk_id, line), media_type="image/png")

    @app.get("/api/hints/suggest")
    def suggest(text: str, p: Principal = Depends(principal)):
        return suggest_evidence(ctx, p, text)

    @app.post("/api/hints")
    def hint(req: HintRequest, p: Principal = Depends(principal)):
        try:
            return {"hint_id": submit_hint(ctx, p, **req.model_dump())}
        except HintError as e:
            raise HTTPException(422, str(e)) from e

    @app.post("/api/feedback")
    def feedback(req: FeedbackRequest, p: Principal = Depends(principal)):
        ctx.ops.add_feedback(req.answer_id, p.oid, req.rating, req.comment)
        return {"ok": True}

    return app


if __name__ == "__main__":
    from docai.runtime.launch import http_app

    http_app(create_app)
