"""The bundle of ports a handler receives, and the registry that lets the composition root supply it.
The factory itself (local or Azure adapters, picked with one setting) lives in docai.app.wiring."""
from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from docai.core.settings import Settings
from docai.ports import (
    AnswerAgent,
    BlobStore,
    ChatModel,
    Clock,
    ContentSafety,
    DocumentConverter,
    Embedder,
    OcrEngine,
    OpsStore,
    Queue,
    Retrieval,
    SearchIndex,
    Verifier,
    VisionModel,
)


@dataclass
class Context:
    settings: Settings
    queue: Queue
    blobs: BlobStore
    ops: OpsStore
    ocr: OcrEngine
    vision: VisionModel
    chat: ChatModel
    embedder: Embedder
    search: SearchIndex
    clock: Clock
    safety: ContentSafety
    agent: AnswerAgent
    retrieval: Retrieval
    verifier: Verifier
    converter: DocumentConverter
    identity: Any = None  # docai.security.auth.DevIdentity or EntraIdentity


_factory: Callable[..., Context] | None = None


def set_context_factory(fn: Callable[..., Context]) -> None:
    global _factory
    _factory = fn


def new_context(settings: Settings | None = None, **kw: Any) -> Context:
    global _factory
    if _factory is None:
        # The single deliberate dynamic import (by name, so the layer test cannot see it): it keeps
        # `python -m docai.modules.<x>` working without docai-run, which registers the factory itself.
        _factory = importlib.import_module("docai.app.wiring").build_context
    return _factory(settings, **kw)
