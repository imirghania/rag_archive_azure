"""The HTTP surface of the internal apps, driven the way app-web drives them: with the signed-in user's bearer token."""
import hashlib

import pytest
from fastapi.testclient import TestClient

from docai.security.access import Principal
from docai.modules import chat_api, retrieval, review, upload_api, verifier
from docai.runtime.runner import drain

from conftest import FIN_EXPERTS, FIN_READERS, FIN_STEWARDS, FIN_TREASURY, HR_READERS

USERS = {
    "layla": Principal("aaaaaaaa-0000-0000-0000-00000000000a", "Layla Hassan", ["DocAI.Reader"], [FIN_READERS]),
    "sara": Principal("aaaaaaaa-0000-0000-0000-000000000001", "Sara Aziz", ["DocAI.Expert"], [FIN_READERS, FIN_EXPERTS, FIN_TREASURY]),
    "rana": Principal("aaaaaaaa-0000-0000-0000-000000000002", "Rana Saleh", ["DocAI.Steward"], [FIN_READERS, FIN_STEWARDS]),
    "yousef": Principal("aaaaaaaa-0000-0000-0000-000000000004", "Yousef Karim", ["DocAI.Admin"], []),
    "huda": Principal("aaaaaaaa-0000-0000-0000-00000000000b", "Huda", ["DocAI.Reader"], [HR_READERS]),
}
LEASE = "FIN-C03-S2-F0117"


class Apps:
    def __init__(self, ctx):
        self.ctx = ctx
        self.chat, self.review, self.upload = (TestClient(m.create_app(ctx)) for m in (chat_api, review, upload_api))
        self.retrieval, self.verifier = TestClient(retrieval.create_app(ctx)), TestClient(verifier.create_app(ctx))

    def h(self, user):
        return {"Authorization": f"Bearer {self.ctx.identity.issue(USERS[user])}"}

    def pump(self):
        for _ in range(10):
            if review.relay_outbox(self.ctx) + drain(self.ctx) == 0:
                return


@pytest.fixture
def apps(ctx):
    ctx.settings.tuning.upload_block_kb = 64
    return Apps(ctx)


def upload_dossier(a: Apps, dossier_id=LEASE, user="sara", names=None):
    d = a.ctx.samples / "dossiers" / dossier_id
    files = {f.name: f.read_bytes() for f in sorted(d.iterdir()) if f.name != "dossier.json" and (names is None or f.name in names)}
    r = a.upload.post("/api/uploads", headers=a.h(user), json={"department": "FIN", "mode": "dossier", "dossier_id": dossier_id,
                      "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in files.items()]})
    assert r.status_code == 200, r.text
    s = r.json()
    for n, b in files.items():
        bs = s["block_bytes"]
        for i in range(0, len(b), bs):
            assert a.upload.put(f"/api/uploads/{s['upload_id']}/files/{n}/blocks/{i // bs}", headers=a.h(user), content=b[i:i + bs]).status_code == 200
    assert a.upload.post(f"/api/uploads/{s['upload_id']}/complete", headers=a.h(user)).status_code == 200
    a.pump()
    return s["upload_id"]


def test_every_endpoint_refuses_a_missing_or_bad_token(apps):
    for client, path in ((apps.chat, "/api/chat"), (apps.review, "/api/review/next"), (apps.upload, "/api/uploads/up-1"),
                         (apps.retrieval, "/search/notes"), (apps.verifier, "/verify")):
        for headers in ({}, {"Authorization": "Bearer garbage"}, {"Authorization": "Basic abc"}):
            r = client.post(path, headers=headers, json={}) if path in ("/api/chat", "/search/notes", "/verify") else client.get(path, headers=headers)
            assert r.status_code == 401, (path, headers)
    assert apps.chat.get("/healthz").status_code == 200


def test_the_whole_story_over_http(apps):
    """Sara uploads; Layla asks and is refused the unverified amount; Sara settles it; Layla gets the answer and opens the citation."""
    a = apps
    uid = upload_dossier(a)
    st = a.upload.get(f"/api/uploads/{uid}", headers=a.h("sara")).json()
    assert st["status"] == "committed" and st["dossiers"][0]["status"] == "completed"

    q = {"question": "How much was approved for the Plot 118 lease renewal?"}
    r1 = a.chat.post("/api/chat", headers=a.h("layla"), json=q).json()
    assert r1["abstained"] and r1["reason"] == "unverified" and "awaiting expert verification" in r1["text"] and "1,7" not in r1["text"]

    t = a.review.get("/api/review/next", headers=a.h("sara")).json()
    assert t["task_id"] == 88412 and t["line_id"] == "L8"
    ev = a.review.get(f"/api/review/{t['task_id']}/evidence", headers=a.h("sara")).json()
    assert [r["engine"] for r in ev["readings"]] == ["ocr", "second_reader"]
    img = a.review.get(f"/api/review/{t['task_id']}/crop", headers=a.h("sara"))
    assert img.status_code == 200 and img.headers["content-type"] == "image/png" and img.content.startswith(b"\x89PNG")
    assert a.review.post(f"/api/review/{t['task_id']}/heartbeat", headers=a.h("sara"), json={"lease_token": t["lease_token"]}).status_code == 200
    d = a.review.post(f"/api/review/{t['task_id']}/decide", headers=a.h("sara"), json={"lease_token": t["lease_token"], "decision": "accept_model"})
    assert d.status_code == 200
    again = a.review.post(f"/api/review/{t['task_id']}/decide", headers=a.h("sara"), json={"lease_token": t["lease_token"], "decision": "accept_model"})
    assert again.status_code == 409, "the lease is spent"
    a.pump()

    r2 = a.chat.post("/api/chat", headers=a.h("layla"), json=q).json()
    assert not r2["abstained"] and "1,750" in r2["text"]
    c = r2["citations"][0]
    crop = a.chat.get(f"/api/citations/{c['chunk_id']}/crop", params={"line": c["ref"]}, headers=a.h("layla"))
    assert crop.status_code == 200 and crop.content.startswith(b"\x89PNG")
    assert a.chat.post("/api/feedback", headers=a.h("layla"), json={"answer_id": r2["answer_id"], "rating": 1}).status_code == 200
    assert a.chat.post("/api/feedback", headers=a.h("layla"), json={"answer_id": "ans-nope", "rating": 1}).status_code == 404


def test_roles_and_departments_are_enforced_per_endpoint(apps):
    a = apps
    upload_dossier(a)
    assert a.review.get("/api/review/next", headers=a.h("layla")).status_code == 204, "a reader has no review queue"
    assert a.review.get("/api/review/next", headers=a.h("huda")).status_code == 204
    assert a.chat.post("/api/chat", headers=a.h("yousef"), json={"question": "anything"}).status_code == 403, "the admin role sees no content"
    assert a.chat.post("/api/chat", headers=a.h("layla"), json={"question": "How much was approved?"}).status_code == 200
    assert a.upload.post("/api/uploads", headers=a.h("layla"), json={"department": "FIN", "mode": "dossier", "dossier_id": LEASE, "files": []}).status_code == 403
    assert a.review.get("/api/hints/awaiting", headers=a.h("sara")).json() == []
    assert a.review.get("/api/admin/status", headers=a.h("sara")).status_code == 403
    assert a.review.get("/api/admin/status", headers=a.h("yousef")).status_code == 200
    assert a.review.post("/api/admin/reprocess", headers=a.h("rana"), json={"dossier_id": LEASE}).status_code == 403
    t = a.review.get("/api/review/next", headers=a.h("sara")).json()
    stolen = a.review.get(f"/api/review/{t['task_id']}/evidence", headers=a.h("huda"))
    assert stolen.status_code == 403, "an HR user cannot read a Finance task even with its ID"
    assert a.review.post(f"/api/review/{t['task_id']}/decide", headers=a.h("layla"),
                         json={"lease_token": t["lease_token"], "decision": "accept_ocr"}).status_code == 403


def test_a_citation_outside_the_callers_scope_looks_like_a_missing_one(apps):
    a = apps
    upload_dossier(a)
    cid = next(iter(a.ctx.search.ids("docs")))
    ref = a.ctx.search.get("docs", cid)["line_refs"][0]
    assert a.chat.get(f"/api/citations/{cid}/crop", params={"line": ref}, headers=a.h("layla")).status_code == 200
    assert a.chat.get(f"/api/citations/{cid}/crop", params={"line": ref}, headers=a.h("huda")).status_code == 404
    assert a.chat.get("/api/citations/FIN-C03-S2-F0117-r1-D09__v1__c0001/crop", params={"line": "p001/L1"}, headers=a.h("layla")).status_code == 404


def test_retrieval_works_out_the_scope_from_the_token_and_ignores_the_body(apps):
    a = apps
    upload_dossier(a)
    q = {"query": "lease Plot 118", "top": 3}
    assert a.retrieval.post("/search/documents", headers=a.h("layla"), json=q).json()
    forged = {**q, "scope": [FIN_READERS], "acl_groups": [FIN_READERS]}
    assert a.retrieval.post("/search/documents", headers=a.h("huda"), json=forged).json() == []


def test_the_verifier_app_checks_against_the_callers_scope(apps):
    a = apps
    cid, ref = "FIN-C03-S2-F0117-r1-D03__v2__c0002", "p005/L8"
    ev = {cid: {"chunk_id": cid, "acl_groups": [FIN_READERS], "trust_tiers_json": '{"p005/L8": "human_verified"}', "lines": [{"ref": ref, "text": "Approved, pay 1,750 by 15/3"}]}}
    body = {"draft": f"Approved, pay 1,750 by 15/3 [c:{cid}#{ref}].", "evidence": ev}
    assert a.verifier.post("/verify", headers=a.h("layla"), json=body).json()["ok"] is True
    out = a.verifier.post("/verify", headers=a.h("huda"), json=body).json()
    assert out["ok"] is False and out["claims"][0]["failed_layer"] == "structure"


def test_hints_over_http_with_the_four_eyes_rule(apps):
    a = apps
    upload_dossier(a)
    body = {"department": "FIN", "type": "context_note", "text": 'Project Falcon was the internal name for the Jebel Ali warehouse expansion.'}
    assert a.chat.post("/api/hints", headers=a.h("layla"), json=body).status_code == 403, "a reader cannot submit hints"
    sug = a.chat.get("/api/hints/suggest", params={"text": "Jebel Ali warehouse"}, headers=a.h("sara")).json()
    assert sug
    r = a.chat.post("/api/hints", headers=a.h("sara"), json={**body, "evidence": [{"chunk_id": sug[0]["chunk_id"], "lines": [sug[0]["lines"][0]["ref"]]}]})
    hid = r.json()["hint_id"]
    bad = a.chat.post("/api/hints", headers=a.h("sara"), json={**body, "evidence": [{"chunk_id": sug[0]["chunk_id"], "lines": ["p999/L1"]}]})
    assert bad.status_code == 422
    a.pump()
    assert [h["hint_id"] for h in a.review.get("/api/hints/awaiting", headers=a.h("rana")).json()] == [hid]
    assert a.review.post(f"/api/hints/{hid}/approve", headers=a.h("sara"), json={}).status_code == 403
    assert a.review.post(f"/api/hints/{hid}/reject", headers=a.h("rana"), json={"reason": " "}).status_code == 422
    assert a.review.post(f"/api/hints/{hid}/approve", headers=a.h("rana"), json={}).status_code == 200
    a.pump()
    inbox = a.review.get("/api/inbox", headers=a.h("sara")).json()
    assert len(inbox) == 1 and "approved" in inbox[0]["title"]
    assert a.review.get("/api/inbox", headers=a.h("layla")).json() == []
    assert a.review.post(f"/api/inbox/{inbox[0]['id']}/read", headers=a.h("layla")).status_code == 404, "somebody else's row looks missing"
    assert a.review.post(f"/api/inbox/{inbox[0]['id']}/read", headers=a.h("sara")).status_code == 200


def test_a_steward_restricts_a_dossier_inside_the_department_and_cannot_widen_beyond_it(apps):
    a = apps
    upload_dossier(a)
    r = a.review.post(f"/api/dossiers/{LEASE}/acl", headers=a.h("rana"), json={"groups": [FIN_TREASURY], "reason": "Treasury only per policy TR-04"})
    assert r.status_code == 200 and r.json()["acl_version"] == 2
    a.pump()
    assert a.ctx.search.get("docs", next(iter(a.ctx.search.ids("docs"))))["acl_groups"] == [FIN_TREASURY]
    assert a.review.post(f"/api/dossiers/{LEASE}/acl", headers=a.h("rana"), json={"groups": [HR_READERS], "reason": "share"}).status_code == 403
    assert a.review.post(f"/api/dossiers/{LEASE}/acl", headers=a.h("rana"), json={"groups": [FIN_READERS], "reason": " "}).status_code == 422
    assert a.review.post(f"/api/dossiers/{LEASE}/acl", headers=a.h("sara"), json={"groups": [FIN_READERS], "reason": "x"}).status_code == 403


def test_the_admin_reprocesses_a_dossier_and_sees_status_but_no_content(apps):
    a = apps
    upload_dossier(a)
    assert a.review.post("/api/admin/reprocess", headers=a.h("yousef"), json={"dossier_id": "FIN-C99-S9-F9999"}).status_code == 404
    assert a.review.post("/api/admin/reprocess", headers=a.h("yousef"), json={"dossier_id": LEASE}).json() == {"revision": 2}
    a.pump()
    rows = {(r["dossier_id"], r["revision"]): r["status"] for r in a.review.get("/api/admin/status", headers=a.h("yousef")).json()}
    assert rows == {(LEASE, 1): "superseded", (LEASE, 2): "completed"}
    assert not any("text" in r for r in a.review.get("/api/admin/status", headers=a.h("yousef")).json())


def test_a_steward_settles_an_escalated_task(apps):
    from docai.adapters.local.clock import FixedClock
    a = apps
    upload_dossier(a)
    clock = FixedClock()
    a.ctx.ops.clock = clock
    for _ in range(3):
        assert a.review.get("/api/review/next", headers=a.h("sara")).status_code == 200
        clock.advance(minutes=16)
    a.review.get("/api/review/next", headers=a.h("sara"))  # counts the third lapse
    esc = [t for t in a.ctx.ops.list_tasks("FIN", "escalated")]
    assert esc
    assert a.review.get("/api/review/escalated/next", headers=a.h("sara")).status_code == 204, "experts do not see the Escalated tab"
    t = a.review.get("/api/review/escalated/next", headers=a.h("rana")).json()
    assert t["task_id"] == esc[0]["task_id"]
    assert a.review.post(f"/api/review/{t['task_id']}/decide", headers=a.h("rana"), json={"lease_token": t["lease_token"], "decision": "illegible"}).status_code == 200


def test_the_review_app_starts_the_outbox_relay_with_the_app_and_stops_it_with_the_app(ctx, monkeypatch):
    """Deployed as `create_app(ctx, relay=True)`. Starlette 1.x has no add_event_handler, which crashed app-review on the first real start (D50)."""
    import threading

    started: list[threading.Event] = []

    def fake_start(c, interval=2.0):
        started.append(threading.Event())
        return started[-1]

    monkeypatch.setattr(review, "start_relay", fake_start)
    with TestClient(review.create_app(ctx, relay=True)) as client:
        assert client.get("/healthz").json() == {"ok": True}
        assert len(started) == 1 and not started[0].is_set(), "the relay runs while the app runs"
    assert started[0].is_set(), "and is told to stop when the app stops"
