"""Local stand-ins for the two internal HTTP apps: they call the module functions directly. The Azure adapters call
app-retrieval and app-verifier over HTTP with the caller's token; the interface is the same."""
from __future__ import annotations

from docai.modules import retrieval, verifier


class LocalRetrieval:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def search_documents(self, *, scope, query, language="en", top=8, filters=None):
        return retrieval.search_documents(self.ctx, scope=scope, query=query, language=language, top=top, filters=filters)

    def search_notes(self, *, scope, query, top=5):
        return retrieval.search_notes(self.ctx, scope=scope, query=query, top=top)


class LocalVerifier:
    def __init__(self, ctx) -> None:
        self.ctx = ctx

    def verify(self, *, draft, evidence, scope):
        return verifier.verify(self.ctx, draft=draft, evidence=evidence, scope=scope)
