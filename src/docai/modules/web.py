"""app-web: the only app with a public address. Server-rendered pages, Entra sign-in with MSAL, and a thin layer that
forwards the signed-in user's own token to the internal apps (spec, Workflow 6, Step 1). It validates the token itself
and holds no data: every decision is made, and every capability checked, by the app that owns the data."""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from docai.security.access import Principal
from docai.security.auth import AuthError
from docai.runtime.context import Context

HERE = Path(__file__).parent


@dataclass
class Backends:
    """httpx clients (or anything with .request) for the internal apps."""
    chat: Any
    review: Any
    upload: Any

    @classmethod
    def from_settings(cls, ctx: Context) -> "Backends":
        s = ctx.settings.services
        return cls(httpx.Client(base_url=s.chat_url, timeout=120, follow_redirects=True), httpx.Client(base_url=s.review_url, timeout=30, follow_redirects=True), httpx.Client(base_url=s.upload_url, timeout=300, follow_redirects=True))


class NeedsLogin(Exception):
    pass


def _nav(p: Principal) -> list[tuple[str, str]]:
    roles = set(p.roles)
    nav = [("/", "Ask")]
    if "DocAI.Expert" in roles:
        nav += [("/upload", "Upload"), ("/review", "Review"), ("/hints", "Hints")]
    if "DocAI.Steward" in roles:
        nav += [("/review", "Review"), ("/hints", "Hints")]
    nav.append(("/inbox", "Inbox"))
    if "DocAI.Admin" in roles:
        nav.append(("/admin", "Admin"))
    seen, out = set(), []
    for item in nav:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def create_app(ctx: Context, backends: Backends | None = None, *, msal_flow=None, dev_users: dict[str, Principal] | None = None) -> FastAPI:
    """`msal_flow` is an object with start(request) -> redirect URL and finish(request) -> (token, name, expires_at); in Azure it is
    MsalFlow. `dev_users` enables the local test sign-in page and is refused when the adapters are not local."""
    if dev_users and ctx.settings.adapters != "local":
        raise RuntimeError("the development sign-in is only available with local adapters")
    if ctx.settings.adapters != "local" and ctx.settings.session_secret.startswith("dev-only"):
        raise RuntimeError("the cookie signing secret is still the development default: set DOCAI_SESSION_SECRET or the Key Vault secret web-session-secret")
    be = backends or Backends.from_settings(ctx)
    app = FastAPI(title="app-web", docs_url=None, redoc_url=None)
    app.add_middleware(SessionMiddleware, secret_key=ctx.settings.session_secret, same_site="lax", https_only=ctx.settings.adapters != "local",
                       max_age=3500, session_cookie="docai_session")
    app.mount("/static", StaticFiles(directory=HERE / "web_static"), name="static")
    templates = Jinja2Templates(directory=str(HERE / "web_templates"))

    @app.middleware("http")
    async def headers(request: Request, call_next):
        r = await call_next(request)
        r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin",
                          "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"})
        return r

    @app.exception_handler(NeedsLogin)
    async def _login(_: Request, __: NeedsLogin):
        return RedirectResponse("/login", status_code=303)

    # -- session ---------------------------------------------------------------------------------------------
    def session_principal(request: Request) -> Principal:
        tok, exp = request.session.get("token"), request.session.get("exp", 0)
        if not tok or exp < time.time():
            request.session.clear()
            raise NeedsLogin()
        try:
            return ctx.identity.validate(tok)
        except AuthError:
            request.session.clear()
            raise NeedsLogin() from None

    def csrf_ok(request: Request, csrf: str | None = None) -> None:
        sent = csrf or request.headers.get("x-csrf-token")
        want = request.session.get("csrf")
        if not want or not sent or not secrets.compare_digest(sent, want):
            raise HTTPException(403, "bad CSRF token")

    async def form_csrf(request: Request, csrf: str = Form("")) -> None:
        csrf_ok(request, csrf)

    def hdr(request: Request) -> dict[str, str]:
        return {"Authorization": f"Bearer {request.session['token']}"}

    def call(request: Request, svc: str, method: str, path: str, **kw) -> httpx.Response:
        r = getattr(be, svc).request(method, path, headers={**hdr(request), **kw.pop("headers", {})}, **kw)
        if r.status_code == 401:
            request.session.clear()
            raise NeedsLogin()
        return r

    def render(request: Request, name: str, p: Principal, **vars: Any) -> HTMLResponse:
        csrf = request.session.setdefault("csrf", secrets.token_urlsafe(24))
        flash = request.session.pop("flash", None)
        return templates.TemplateResponse(request, name, {"nav": _nav(p), "user": p.name, "csrf": csrf, "flash": flash, "department": "FIN",
                                                          "can_hint": "DocAI.Expert" in p.roles, **vars})

    def flash(request: Request, text: str) -> None:
        request.session["flash"] = text

    def problem(r: httpx.Response) -> str:
        if r.status_code == 403:
            return "You are not allowed to do that."
        try:
            return str(r.json().get("detail") or r.json())
        except Exception:  # noqa: BLE001
            return f"Something went wrong ({r.status_code})."

    # -- sign-in -----------------------------------------------------------------------------------------------
    @app.get("/login", response_class=HTMLResponse)
    def login(request: Request):
        request.session.setdefault("csrf", secrets.token_urlsafe(24))
        return templates.TemplateResponse(request, "login.html", {"nav": [], "user": None, "csrf": request.session["csrf"], "flash": None,
                                                                  "dev_users": sorted(dev_users) if dev_users else []})

    @app.get("/dev-login")
    def dev_login(request: Request, user: str):
        if not dev_users or user not in dev_users:
            raise HTTPException(404)
        request.session.clear()
        request.session.update(token=ctx.identity.issue(dev_users[user]), name=dev_users[user].name, exp=time.time() + 3400, csrf=secrets.token_urlsafe(24))
        return RedirectResponse("/", status_code=303)

    @app.get("/auth/login")
    def auth_login(request: Request):
        if msal_flow is None:
            raise HTTPException(503, "sign-in is not configured")
        return RedirectResponse(msal_flow.start(request), status_code=303)

    @app.get("/auth/callback")
    def auth_callback(request: Request):
        token, name, exp = msal_flow.finish(request)
        request.session.clear()
        request.session.update(token=token, name=name, exp=exp, csrf=secrets.token_urlsafe(24))
        return RedirectResponse("/", status_code=303)

    @app.get("/logout")
    def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    # -- ask ---------------------------------------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, p: Principal = Depends(session_principal)):
        return render(request, "ask.html", p, answer=None, question="", conversation_id=request.session.get("conversation_id"))

    @app.post("/ask", response_class=HTMLResponse, dependencies=[Depends(form_csrf)])
    def ask(request: Request, question: str = Form(...), conversation_id: str = Form(""), p: Principal = Depends(session_principal)):
        r = call(request, "chat", "POST", "/api/chat", json={"question": question, "conversation_id": conversation_id or request.session.get("conversation_id")})
        if r.status_code != 200:
            flash(request, problem(r))
            return RedirectResponse("/", status_code=303)
        a = r.json()
        request.session["conversation_id"] = a["conversation_id"]
        return render(request, "ask.html", p, answer=type("A", (), {**a, "citations": [type("C", (), c) for c in a["citations"]]}), question=question, conversation_id=a["conversation_id"])

    @app.post("/feedback", dependencies=[Depends(form_csrf)])
    def feedback(request: Request, answer_id: str = Form(...), rating: int = Form(...), p: Principal = Depends(session_principal)):
        r = call(request, "chat", "POST", "/api/feedback", json={"answer_id": answer_id, "rating": rating})
        flash(request, "Thank you." if r.status_code == 200 else problem(r))
        return RedirectResponse("/", status_code=303)

    @app.get("/citation", response_class=HTMLResponse)
    def citation(request: Request, chunk: str, line: str, p: Principal = Depends(session_principal)):
        return render(request, "citation.html", p, chunk=chunk, line=line)

    @app.get("/citation/crop")
    def citation_crop(request: Request, chunk: str, line: str, p: Principal = Depends(session_principal)):
        r = call(request, "chat", "GET", f"/api/citations/{chunk}/crop", params={"line": line})
        return Response(r.content, status_code=r.status_code, media_type=r.headers.get("content-type", "image/png"))

    # -- upload: pages and a pass-through for the block API ------------------------------------------------------------
    @app.get("/upload", response_class=HTMLResponse)
    def upload_page(request: Request, p: Principal = Depends(session_principal)):
        return render(request, "upload.html", p, status=None)

    @app.get("/upload/{upload_id}", response_class=HTMLResponse)
    def upload_status(request: Request, upload_id: str, p: Principal = Depends(session_principal)):
        r = call(request, "upload", "GET", f"/api/uploads/{upload_id}")
        if r.status_code != 200:
            flash(request, problem(r))
            return RedirectResponse("/upload", status_code=303)
        d = r.json()
        return render(request, "upload.html", p, status=type("S", (), {**d, "dossiers": [type("D", (), x) for x in d["dossiers"]]}))

    @app.api_route("/api/uploads", methods=["POST"])
    @app.api_route("/api/uploads/{rest:path}", methods=["GET", "POST", "PUT"])
    async def upload_proxy(request: Request, rest: str = "", p: Principal = Depends(session_principal)):
        if request.method != "GET":
            csrf_ok(request)
        path = "/api/uploads" + (f"/{rest}" if rest else "")
        r = call(request, "upload", request.method, path, content=await request.body() if request.method in ("POST", "PUT") else None,
                 headers={"content-type": request.headers.get("content-type", "application/json")})
        return Response(r.content, status_code=r.status_code, media_type=r.headers.get("content-type", "application/json"))

    # -- review -----------------------------------------------------------------------------------------------
    def task_page(request: Request, p: Principal, task: dict | None):
        readings = []
        if task:
            ev = call(request, "review", "GET", f"/api/review/{task['task_id']}/evidence")
            readings = ev.json()["readings"] if ev.status_code == 200 else []
        return render(request, "review.html", p, task=type("T", (), task) if task else None, readings=[type("R", (), x) for x in readings],
                      can_escalated="DocAI.Steward" in p.roles)

    @app.get("/review", response_class=HTMLResponse)
    def review_page(request: Request, p: Principal = Depends(session_principal)):
        return task_page(request, p, None)

    @app.post("/review/next", response_class=HTMLResponse, dependencies=[Depends(form_csrf)])
    def review_next(request: Request, p: Principal = Depends(session_principal)):
        r = call(request, "review", "GET", "/api/review/next")
        return task_page(request, p, r.json() if r.status_code == 200 else None)

    @app.post("/review/escalated", response_class=HTMLResponse, dependencies=[Depends(form_csrf)])
    def review_escalated(request: Request, p: Principal = Depends(session_principal)):
        r = call(request, "review", "GET", "/api/review/escalated/next")
        return task_page(request, p, r.json() if r.status_code == 200 else None)

    @app.get("/review/{task_id}/crop")
    def review_crop(request: Request, task_id: int, context: bool = False, p: Principal = Depends(session_principal)):
        r = call(request, "review", "GET", f"/api/review/{task_id}/crop", params={"context": str(context).lower()})
        return Response(r.content, status_code=r.status_code, media_type=r.headers.get("content-type", "image/png"))

    @app.post("/review/{task_id}/heartbeat")
    async def review_beat(request: Request, task_id: int, p: Principal = Depends(session_principal)):
        csrf_ok(request)
        r = call(request, "review", "POST", f"/api/review/{task_id}/heartbeat", content=await request.body(), headers={"content-type": "application/json"})
        return Response(r.content, status_code=r.status_code, media_type="application/json")

    @app.post("/review/{task_id}/decide", dependencies=[Depends(form_csrf)])
    def review_decide(request: Request, task_id: int, lease_token: str = Form(...), decision: str = Form(...), text: str = Form(""),
                      p: Principal = Depends(session_principal)):
        r = call(request, "review", "POST", f"/api/review/{task_id}/decide", json={"lease_token": lease_token, "decision": decision, "text": text or None})
        flash(request, "Saved. Thank you." if r.status_code == 200 else ("This task was reassigned while you were away." if r.status_code == 409 else problem(r)))
        return RedirectResponse("/review", status_code=303)

    # -- hints ----------------------------------------------------------------------------------------------------
    @app.get("/hints", response_class=HTMLResponse)
    def hints_page(request: Request, p: Principal = Depends(session_principal)):
        aw = call(request, "review", "GET", "/api/hints/awaiting") if "DocAI.Steward" in p.roles else None
        rows = [type("H", (), h) for h in aw.json()] if aw is not None and aw.status_code == 200 else (None if "DocAI.Steward" not in p.roles else [])
        return render(request, "hints.html", p, awaiting=rows, from_answer=None)

    @app.get("/hints/new", response_class=HTMLResponse)
    def hints_new(request: Request, from_answer: str = "", p: Principal = Depends(session_principal)):
        return render(request, "hints.html", p, awaiting=None, from_answer=from_answer)

    @app.post("/hints", dependencies=[Depends(form_csrf)])
    def hint_submit(request: Request, department: str = Form(...), type: str = Form(...), text: str = Form(...), terms: str = Form(""),
                    chunk_id: str = Form(""), line: str = Form(""), from_answer: str = Form(""), p: Principal = Depends(session_principal)):
        body = {"department": department, "type": type, "text": text, "from_answer": from_answer or None,
                "terms": [t.strip() for t in terms.splitlines() if t.strip()] or None,
                "evidence": [{"chunk_id": chunk_id, "lines": [line]}] if chunk_id and line else None}
        r = call(request, "chat", "POST", "/api/hints", json=body)
        flash(request, f"Hint {r.json()['hint_id']} was submitted for approval." if r.status_code == 200 else problem(r))
        return RedirectResponse("/hints", status_code=303)

    @app.post("/hints/{hint_id}", dependencies=[Depends(form_csrf)])
    def hint_decide(request: Request, hint_id: str, action: str = Form(...), reason: str = Form(""), p: Principal = Depends(session_principal)):
        if action not in ("approve", "reject"):
            raise HTTPException(400)
        r = call(request, "review", "POST", f"/api/hints/{hint_id}/{action}", json={"reason": reason} if action == "reject" else {})
        flash(request, "Done." if r.status_code == 200 else problem(r))  # 403 covers both a missing steward role and the four-eyes rule
        return RedirectResponse("/hints", status_code=303)

    # -- inbox and admin ---------------------------------------------------------------------------------------------
    @app.get("/inbox", response_class=HTMLResponse)
    def inbox(request: Request, p: Principal = Depends(session_principal)):
        r = call(request, "review", "GET", "/api/inbox")
        return render(request, "inbox.html", p, messages=[type("M", (), m) for m in (r.json() if r.status_code == 200 else [])])

    @app.post("/inbox/{inbox_id}/read", dependencies=[Depends(form_csrf)])
    def inbox_read(request: Request, inbox_id: int, p: Principal = Depends(session_principal)):
        call(request, "review", "POST", f"/api/inbox/{inbox_id}/read")
        return RedirectResponse("/inbox", status_code=303)

    @app.get("/admin", response_class=HTMLResponse)
    def admin(request: Request, p: Principal = Depends(session_principal)):
        r = call(request, "review", "GET", "/api/admin/status")
        if r.status_code == 403:
            raise HTTPException(403, "the admin role is required")
        return render(request, "admin.html", p, dossiers=[type("D", (), d) for d in r.json()])

    @app.post("/admin/reprocess", dependencies=[Depends(form_csrf)])
    def admin_reprocess(request: Request, dossier_id: str = Form(...), p: Principal = Depends(session_principal)):
        r = call(request, "review", "POST", "/api/admin/reprocess", json={"dossier_id": dossier_id})
        flash(request, f"Reprocessing {dossier_id} as revision {r.json()['revision']}." if r.status_code == 200 else problem(r))
        return RedirectResponse("/admin", status_code=303)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


class MsalFlow:
    """The authorization-code flow of a confidential web app (docai-web). The secret comes from Key Vault in Azure."""

    def __init__(self, ctx: Context, client_secret: str) -> None:
        import msal

        a = ctx.settings.auth
        self.scopes = [f"api://{a.api_client_id}/access_as_user"]
        self.redirect = ctx.settings.web_redirect_url
        self.app = msal.ConfidentialClientApplication(a.web_client_id, authority=f"https://login.microsoftonline.com/{a.tenant_id}", client_credential=client_secret)

    def start(self, request: Request) -> str:
        # Signing out only clears this app's cookie; the Microsoft session survives. Without a prompt Microsoft signs the same account
        # in again at once. `select_account` always shows the account picker (D53).
        flow = self.app.initiate_auth_code_flow(self.scopes, redirect_uri=self.redirect, prompt="select_account")
        request.session["auth_flow"] = flow
        return flow["auth_uri"]

    def finish(self, request: Request) -> tuple[str, str, float]:
        flow = request.session.pop("auth_flow", None)
        if not flow:
            raise HTTPException(400, "no sign-in in progress")
        result = self.app.acquire_token_by_auth_code_flow(flow, dict(request.query_params))
        if "access_token" not in result:
            raise HTTPException(401, result.get("error_description", "sign-in failed"))
        return result["access_token"], result.get("id_token_claims", {}).get("name", ""), time.time() + int(result.get("expires_in", 3500)) - 60


if __name__ == "__main__":
    from docai.runtime.launch import web_app

    web_app(create_app, MsalFlow)
