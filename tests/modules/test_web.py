"""app-web in front of the real internal apps: sign-in, CSRF, pages by role, the upload pass-through, review, hints, admin."""
import hashlib
import re

import pytest
from fastapi.testclient import TestClient

from docai.devtools.localdev import DEV_USERS, build_local_web
from docai.modules import review
from docai.runtime.runner import drain

LEASE = "FIN-C03-S2-F0117"


@pytest.fixture
def web(ctx):
    ctx.settings.tuning.upload_block_kb = 64
    # the ctx fixture seeds its own group IDs; make the dev users' groups match them
    import docai.devtools.localdev as ld
    ld.seed_registry(ctx)
    return ctx, build_local_web(ctx)


def login(app, user):
    c = TestClient(app, follow_redirects=False)
    assert c.get(f"/dev-login?user={user}").status_code == 303
    return c


def csrf_of(client) -> str:
    return re.search(r'name="csrf" content="([^"]+)"', client.get("/").text).group(1)


def pump(ctx):
    for _ in range(10):
        if review.relay_outbox(ctx) + drain(ctx) == 0:
            return


def test_pages_need_a_session_and_the_cookie_cannot_be_forged(web):
    ctx, app = web
    c = TestClient(app, follow_redirects=False)
    for path in ("/", "/upload", "/review", "/hints", "/inbox", "/admin", "/citation?chunk=x&line=y"):
        r = c.get(path)
        assert r.status_code == 303 and r.headers["location"] == "/login", path
    assert "Layla" not in c.get("/login").text and "sara" in c.get("/login").text
    c.cookies.set("docai_session", "forged.cookie.value")
    assert c.get("/").status_code == 303
    assert c.get("/dev-login?user=nobody").status_code == 404


def test_a_token_the_identity_refuses_ends_the_session(web):
    from unittest.mock import patch
    from docai.security.auth import AuthError
    ctx, app = web
    c = login(app, "layla")
    assert c.get("/").status_code == 200
    with patch.object(type(ctx.identity), "validate", side_effect=AuthError("expired")):
        assert c.get("/").status_code == 303
    assert c.get("/").status_code == 303, "the session was cleared, not just refused once"


def test_the_navigation_shows_only_what_each_role_can_use(web):
    ctx, app = web
    nav = lambda u: re.findall(r'<header>.*?</header>', login(app, u).get("/").text, re.S)[0]  # noqa: E731
    assert "Upload" not in nav("layla") and "Review" not in nav("layla") and "Admin" not in nav("layla")
    assert all(x in nav("sara") for x in ("Upload", "Review", "Hints")) and "Admin" not in nav("sara")
    assert "Hints" in nav("rana") and "Upload" not in nav("rana")
    assert "Admin" in nav("yousef") and "Upload" not in nav("yousef")


def test_security_headers_and_csrf_on_every_post(web):
    ctx, app = web
    c = login(app, "layla")
    r = c.get("/")
    assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"] and r.headers["x-content-type-options"] == "nosniff"
    assert c.post("/ask", data={"question": "hi"}).status_code == 403
    assert c.post("/ask", data={"question": "hi", "csrf": "wrong"}).status_code == 403
    assert c.post("/api/uploads", json={}).status_code == 403
    assert c.post("/feedback", data={"answer_id": "a", "rating": 1}).status_code == 403
    assert c.post("/ask", data={"question": "hi", "csrf": csrf_of(c)}).status_code in (200, 303)


def test_the_browser_story_upload_ask_review_hint_inbox_admin(web):
    ctx, app = web
    sara, layla, rana, yousef = (login(app, u) for u in ("sara", "layla", "rana", "yousef"))

    # Sara uploads through the pass-through, exactly as upload.js does
    d = ctx.samples / "dossiers" / LEASE
    files = {f.name: f.read_bytes() for f in sorted(d.iterdir()) if f.name != "dossier.json"}
    tok = csrf_of(sara)
    H = {"X-CSRF-Token": tok}
    opened = sara.post("/api/uploads", headers=H, json={"department": "FIN", "mode": "dossier", "dossier_id": LEASE,
                       "files": [{"name": n, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in files.items()]})
    assert opened.status_code == 200 and "does not exist yet" in opened.json()["decisive_line"]
    up = opened.json()
    for n, b in files.items():
        for i in range(0, len(b), up["block_bytes"]):
            r = sara.put(f"/api/uploads/{up['upload_id']}/files/{n}/blocks/{i // up['block_bytes']}", headers=H, content=b[i:i + up["block_bytes"]])
            assert r.status_code == 200
    assert sara.post(f"/api/uploads/{up['upload_id']}/complete", headers=H).status_code == 200
    pump(ctx)
    page = sara.get(f"/upload/{up['upload_id']}").text
    assert "committed" in page and LEASE in page and "completed" in page

    # Layla asks and is told the amount awaits verification; she cannot hint
    t = csrf_of(layla)
    a1 = layla.post("/ask", data={"question": "How much was approved for the Plot 118 lease renewal?", "csrf": t})
    assert a1.status_code == 200 and "awaiting expert verification" in a1.text and "Add expert hint" not in a1.text

    # Sara settles the task in the review page
    rt = csrf_of(sara)
    nxt = sara.post("/review/next", data={"csrf": rt})
    assert "Task 88412" in nxt.text and "Accept second reader" in nxt.text
    lease = re.search(r'name="lease_token" value="([^"]+)"', nxt.text).group(1)
    assert sara.get("/review/88412/crop").content.startswith(b"\x89PNG")
    assert layla.get("/review/88412/crop").status_code == 403, "a reader has no review rights even with the task ID"
    done = sara.post("/review/88412/decide", data={"csrf": rt, "lease_token": lease, "decision": "accept_model"})
    assert done.status_code == 303
    assert "Saved" in sara.get("/review").text
    sara.post("/review/88412/decide", data={"csrf": rt, "lease_token": lease, "decision": "accept_model"})  # the lease is spent
    assert "reassigned" in sara.get("/review").text
    pump(ctx)

    a2 = layla.post("/ask", data={"question": "How much was approved for the Plot 118 lease renewal?", "csrf": t})
    assert "1,750" in a2.text and "/citation?chunk=" in a2.text
    link = re.search(r'href="(/citation\?chunk=[^"]+)"', a2.text).group(1).replace("&amp;", "&")
    assert layla.get(link).status_code == 200
    crop = layla.get(link.replace("/citation?", "/citation/crop?"))
    assert crop.status_code == 200 and crop.content.startswith(b"\x89PNG")

    # Sara submits a hint, Rana approves it, Sara finds it in her inbox
    hs = csrf_of(sara)
    r = sara.post("/hints", data={"csrf": hs, "department": "FIN", "type": "context_note", "text": "Project Falcon is the Jebel Ali warehouse expansion."})
    assert r.status_code == 303 and "was submitted for approval" in sara.get("/hints").text
    pump(ctx)
    hid = re.search(r"hint-\d{6}", rana.get("/hints").text).group(0)
    assert "Approve" in rana.get("/hints").text and "Approve" not in sara.get("/hints").text
    sara.post(f"/hints/{hid}", data={"csrf": hs, "action": "approve"})
    assert "not allowed" in sara.get("/hints").text, "an expert cannot approve"
    assert rana.post(f"/hints/{hid}", data={"csrf": csrf_of(rana), "action": "approve"}).status_code == 303
    pump(ctx)
    assert "approved by Rana Saleh" in sara.get("/inbox").text

    # Yousef sees status and reprocesses; Sara is refused the page
    assert sara.get("/admin").status_code == 403
    assert LEASE in yousef.get("/admin").text
    assert yousef.post("/admin/reprocess", data={"csrf": csrf_of(yousef), "dossier_id": LEASE}).status_code == 303
    assert "revision 2" in yousef.get("/admin").text
    assert "Reprocess" in yousef.get("/admin").text


def test_the_development_sign_in_cannot_be_enabled_outside_local_mode(web):
    from docai.modules import web as webmod
    ctx, _ = web
    ctx.settings.adapters = "azure"
    with pytest.raises(RuntimeError):
        webmod.create_app(ctx, webmod.Backends(None, None, None), dev_users=DEV_USERS)


def test_sign_in_always_asks_which_account(monkeypatch):
    """After a sign-out the Microsoft session is still alive; without a prompt it would sign the same account in again (D53)."""
    import inspect
    from types import SimpleNamespace

    import msal

    from docai.modules import web as webmod

    assert "prompt" in inspect.signature(msal.ConfidentialClientApplication.initiate_auth_code_flow).parameters, "the installed MSAL knows `prompt`"
    seen = {}

    def fake_initiate(scopes, redirect_uri=None, **kw):
        seen.update(kw)
        return {"auth_uri": "https://login.example/authorize"}

    flow = webmod.MsalFlow.__new__(webmod.MsalFlow)
    flow.app, flow.scopes, flow.redirect = SimpleNamespace(initiate_auth_code_flow=fake_initiate), ["api://x/access_as_user"], "https://app/auth/callback"
    request = SimpleNamespace(session={})
    assert flow.start(request) == "https://login.example/authorize" and seen["prompt"] == "select_account"
    assert "auth_flow" in request.session
