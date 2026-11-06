"""Plain dataclasses that the ports pass around: queue deliveries, ops-store rows, search hits and verdicts.
They import contracts only, never `ports`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from docai.contracts.messages import Envelope


@dataclass
class Delivery:
    """A message received in peek-lock mode. Settle it through the queue that produced it."""
    envelope: Envelope
    message_id: str
    queue: str
    delivery_count: int
    session_id: str | None = None
    token: Any = None


@dataclass
class SearchHit:
    id: str
    score: float
    doc: dict[str, Any]


# ops store
@dataclass
class RegisterResult:
    status: str  # registered | duplicate | stale
    revision: int
    files_to_prepare: int = 0
    acl_groups: list[str] = field(default_factory=list)


@dataclass
class Dossier:
    dossier_id: str
    revision: int
    department: str
    status: str
    priority: str
    total_pages: int | None
    pages_done: int
    pages_failed: int
    files_to_prepare: int
    segmented: bool
    documents_total: int
    acl_groups: list[str]
    acl_version: int
    manifest_hash: str
    manifest_path: str
    segmentation: str


@dataclass
class FileRow:
    name: str
    seq: int
    type: str
    route: str
    status: str
    location: str
    pages: int | None
    sha256: str = ""


@dataclass
class PageRow:
    page_no: int
    status: str
    source_file: str
    frame: int
    text_layer: bool
    flagged_lines: int


@dataclass
class DocumentRow:
    document_id: str
    dossier_id: str
    revision: int
    seq: int
    first_page: int
    last_page: int
    status: str
    current_version: int
    indexed_version: int | None
    has_gaps: bool
    title: str | None


@dataclass
class OutboxRow:
    id: int
    message_id: str
    destination: str
    session_id: str | None
    body: str


# content safety
@dataclass
class ShieldResult:
    question_attack: bool = False
    document_attacks: list[bool] = field(default_factory=list)


# answering services
@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ClaimResult:
    claim_id: int
    text: str
    citations: list[str]  # "chunk_id#p014/L17"
    verdict: str  # supported | partial | unsupported
    failed_layer: str | None = None  # structure | trust_tier | numbers | entailment
    detail: str = ""


@dataclass
class Verdict:
    claims: list[ClaimResult]
    blocked_lines: list[str]  # line keys cited by claims that the trust-tier layer rejected

    @property
    def supported(self) -> list[ClaimResult]:
        return [c for c in self.claims if c.verdict == "supported"]

    @property
    def ok(self) -> bool:
        return bool(self.claims) and all(c.verdict == "supported" for c in self.claims)
