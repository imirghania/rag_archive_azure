"""Ports: the small interfaces that hide Azure (spec, Ports). Each has an Azure adapter and a local fake.
Modules depend on these and on `contracts`, never on each other and never on an Azure SDK.
The row and result dataclasses the ports pass around live in `docai.schemas.rows` and are re-exported here."""
from __future__ import annotations

from docai.schemas.rows import (
    ClaimResult,
    Delivery,
    DocumentRow,
    Dossier,
    FileRow,
    OutboxRow,
    PageRow,
    RegisterResult,
    SearchHit,
    ShieldResult,
    ToolCall,
    Verdict,
)

from .answering import AnswerAgent, Retrieval, ToolExecutor, Verifier
from .blobs import AlreadyExists, BlobStore, LeaseLost
from .models import (
    ChatModel,
    Clock,
    ContentSafety,
    DocumentConverter,
    Embedder,
    OcrEngine,
    VisionModel,
)
from .ops import OpsStore, ReviewOps
from .queue import Queue
from .search import SearchIndex

__all__ = [
    "AlreadyExists", "AnswerAgent", "BlobStore", "ChatModel", "ClaimResult", "Clock", "ContentSafety", "Delivery",
    "DocumentConverter", "DocumentRow", "Dossier", "Embedder", "FileRow", "LeaseLost", "OcrEngine", "OpsStore",
    "OutboxRow", "PageRow", "Queue", "RegisterResult", "Retrieval", "ReviewOps", "SearchHit", "SearchIndex",
    "ShieldResult", "ToolCall", "ToolExecutor", "Verdict", "Verifier", "VisionModel",
]
