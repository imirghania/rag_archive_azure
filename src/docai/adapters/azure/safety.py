"""ContentSafety adapter: Prompt Shields (user-prompt and document attacks) over REST with the app's Entra token."""
from __future__ import annotations

from typing import Any

import httpx

from docai.ports import ShieldResult

API = "2024-09-01"
MAX_CHARS, MAX_DOCS = 10_000, 5  # documented request limits


class PromptShields:
    def __init__(self, endpoint: str, credential: Any = None, *, http: httpx.Client | None = None) -> None:
        from azure.identity import DefaultAzureCredential

        self.url = endpoint.rstrip("/") + f"/contentsafety/text:shieldPrompt?api-version={API}"
        self.cred, self.http = credential or DefaultAzureCredential(), http or httpx.Client(timeout=30)

    def _post(self, prompt: str, docs: list[str]) -> dict:
        token = self.cred.get_token("https://cognitiveservices.azure.com/.default").token
        r = self.http.post(self.url, 
                        headers={"Authorization": f"Bearer {token}"}, 
                        json={
                            "userPrompt": prompt[:MAX_CHARS], 
                            "documents": [d[:MAX_CHARS] for d in docs]
                            }
                        )
        r.raise_for_status()
        return r.json()

    def shield(self, *, question: str | None = None, documents: list[str] | None = None) -> ShieldResult:
        docs = documents or []
        attacks: list[bool] = []
        q_attack = False
        for i in range(0, max(len(docs), 1), MAX_DOCS):  # at most five documents per request
            batch = docs[i:i + MAX_DOCS]
            if not batch and (question is None or i > 0):
                break
            out = self._post(question if (question is not None and i == 0) else "", batch)
            if i == 0 and question is not None:
                q_attack = bool(out.get("userPromptAnalysis", {}).get("attackDetected"))
            attacks += [bool(d.get("attackDetected")) for d in out.get("documentsAnalysis", [])]
        return ShieldResult(q_attack, attacks)
