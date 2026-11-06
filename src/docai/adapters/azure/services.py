"""Clients of app-retrieval and app-verifier. They forward the signed-in user's own token: the server works out the access scope
from it, so a caller cannot ask for more than the user may see. `scope` is accepted for port compatibility and ignored."""
from __future__ import annotations

from typing import Any

import httpx

from docai.ports import ClaimResult, Verdict
from docai.security.tokens import current_token


def _headers() -> dict[str, str]:
    tok = current_token.get()
    if not tok:
        raise RuntimeError("no user token in this request: the retrieval and verifier apps only answer on behalf of a signed-in user")
    return {"Authorization": f"Bearer {tok}"}


class HttpRetrieval:
    def __init__(self, base_url: str, client: Any = None) -> None:
        self.http = client or httpx.Client(base_url=base_url, timeout=60, follow_redirects=True)

    def _post(self, path: str, body: dict) -> list[dict[str, Any]]:
        r = self.http.post(path, headers=_headers(), json=body)
        r.raise_for_status()
        return r.json()

    def search_documents(self, *, scope, query, language="en", top=8, filters=None):
        return self._post("/search/documents", 
                        {
                            "query": query, 
                            "language": language, 
                            "top": top, 
                            "filters": filters
                        })

    def search_notes(self, *, scope, query, top=5):
        return self._post("/search/notes", 
                        {"query": query, "top": top}
                        )


class HttpVerifier:
    def __init__(self, base_url: str, client: Any = None) -> None:
        self.http = client or httpx.Client(base_url=base_url, timeout=120, follow_redirects=True)

    def verify(self, *, draft, evidence, scope):
        r = self.http.post("/verify", 
                        headers=_headers(), 
                        json={"draft": draft, "evidence": evidence}
                        )
        r.raise_for_status()
        d = r.json()
        return Verdict([ClaimResult(**c) for c in d["claims"]], 
                    d["blocked_lines"])
