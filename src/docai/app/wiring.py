"""The composition root: picks local or Azure adapters with one setting and builds the Context.
The ops store is PostgreSQL (SqlOps) in both modes; only the `database` settings differ."""
from __future__ import annotations

from pathlib import Path

from docai.core.settings import Settings
from docai.runtime.context import Context


def build_context(settings: Settings | None = None, *, root: Path | None = None) -> Context:
    s = settings or Settings()
    if s.adapters == "local":
        from docai.adapters.local.agent import ScriptedAgent
        from docai.adapters.local.blobs import LocalBlobStore
        from docai.adapters.local.clock import SystemClock
        from docai.adapters.local.convert import PurePdfConverter
        from docai.adapters.local.models import (
            FixtureOcr,
            FixtureVision,
            HashEmbedder,
            RuleShield,
            ScriptedChat,
        )
        from docai.adapters.local.queue import LocalQueue
        from docai.adapters.local.search import MemorySearch
        from docai.adapters.sql.ops import ops_store

        from .local_services import LocalRetrieval, LocalVerifier

        base = Path(root or s.local_dir)
        clock = SystemClock()
        c = Context(s, LocalQueue(clock), LocalBlobStore(base / "blobs"), 
                    ops_store(s), FixtureOcr(s.local_fixtures_dir),
                    FixtureVision(s.local_fixtures_dir), ScriptedChat(), 
                    HashEmbedder(s.models.embedding_dimensions),
                    MemorySearch(), clock, RuleShield(), ScriptedAgent(), 
                    None, None, PurePdfConverter())  # type: ignore[arg-type]
        c.retrieval, c.verifier = LocalRetrieval(c), LocalVerifier(c)  # they need the context itself
        from docai.security.auth import build_identity
        c.identity = build_identity(s)
        return c
    return _build_azure(s)


def _build_azure(s: Settings) -> Context:
    """Every adapter is created lazily: nothing here talks to Azure until a port is used, so app-web can build the same context
    although it has no access to SQL or storage."""
    from azure.identity import DefaultAzureCredential

    from docai.adapters.azure.agent import FoundryAnswerAgent
    from docai.adapters.azure.blobs import AdlsBlobStore
    from docai.adapters.azure.convert import LibreOfficeConverter
    from docai.adapters.azure.models import FoundryChat, FoundryEmbedder, FoundryVision
    from docai.adapters.azure.ocr import DocumentIntelligenceOcr
    from docai.adapters.azure.queue import ServiceBusQueue
    from docai.adapters.azure.safety import PromptShields
    from docai.adapters.azure.search import AzureSearch
    from docai.adapters.azure.services import HttpRetrieval, HttpVerifier
    from docai.adapters.local.clock import SystemClock
    from docai.adapters.sql.ops import ops_store
    from docai.security.auth import build_identity

    if s.ocr_engine != "document_intelligence":
        raise NotImplementedError("only the Document Intelligence Layout adapter exists; a Content Understanding adapter plugs into the same OcrEngine port")
    a, cred = s.azure, DefaultAzureCredential()
    return Context(s, ServiceBusQueue(a.servicebus_namespace, cred), 
                AdlsBlobStore(s, cred), ops_store(s), 
                DocumentIntelligenceOcr(a.ocr_endpoint, cred),
                FoundryVision(s), FoundryChat(s), FoundryEmbedder(s),
                AzureSearch(a.search_endpoint, cred), SystemClock(), 
                PromptShields(a.content_safety_endpoint, cred),
                FoundryAnswerAgent(s), HttpRetrieval(s.services.retrieval_url), 
                HttpVerifier(s.services.verifier_url), LibreOfficeConverter(), 
                build_identity(s))
