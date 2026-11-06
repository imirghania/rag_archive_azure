"""Status values and the trust-tier table. These are part of the `ops` state contract."""
from __future__ import annotations

from enum import StrEnum


class Priority(StrEnum):
    online = "online"
    bulk = "bulk"  # reserved for the backfill


class TrustTier(StrEnum):
    illegible = "illegible"
    missing = "missing"
    unverified = "unverified"
    handwritten_majority = "handwritten_majority"  # reserved: third reader
    handwritten_dual_agreed = "handwritten_dual_agreed"
    handwritten_triple_agreed = "handwritten_triple_agreed"  # reserved: third reader
    printed_high_conf = "printed_high_conf"
    digital_source = "digital_source"
    human_verified = "human_verified"

    @property
    def rank(self) -> int:
        return _RANK[self]

    @property
    def citable(self) -> bool:
        return self.rank >= 2


_RANK = {
    TrustTier.illegible: 0,
    TrustTier.missing: 0,
    TrustTier.unverified: 1,
    TrustTier.handwritten_majority: 2,
    TrustTier.handwritten_dual_agreed: 3,
    TrustTier.handwritten_triple_agreed: 4,
    TrustTier.printed_high_conf: 5,
    TrustTier.digital_source: 6,
    TrustTier.human_verified: 7,
}
RESERVED_TIERS = frozenset({
    TrustTier.handwritten_majority, 
    TrustTier.handwritten_triple_agreed
    })


def min_tier(tiers: list[TrustTier]) -> TrustTier:
    """The lowest rank wins. For equal ranks (illegible vs missing) the first listed wins."""
    if not tiers:
        return TrustTier.missing
    return min(tiers, key=lambda t: t.rank)


class DossierStatus(StrEnum):
    received = "received"
    preparing = "preparing"  # waiting for conversions
    preprocessing = "preprocessing"
    processing = "processing"
    segmenting = "segmenting"
    indexing = "indexing"
    completed = "completed"
    partial = "partial"
    failed = "failed"
    failed_intake = "failed_intake"
    superseded = "superseded"  # replaced by a newer revision at the swap


class FileRoute(StrEnum):
    scan = "scan"
    digital = "digital"


class FileStatus(StrEnum):
    registered = "registered"
    converting = "converting"
    ready = "ready"
    failed = "failed"


class PageStatus(StrEnum):
    preprocessed = "preprocessed"
    ocr_done = "ocr_done"
    awaiting_second_read = "awaiting_second_read"
    reconciled = "reconciled"  # final
    failed = "failed"  # final
    # awaiting_arbitration is reserved for the third reader


PAGE_FINAL = frozenset({PageStatus.reconciled, PageStatus.failed})


class DocumentStatus(StrEnum):
    segmented = "segmented"
    described = "described"
    chunked = "chunked"
    indexed = "indexed"
    removed = "removed"


class TaskStatus(StrEnum):
    open = "open"
    claimed = "claimed"
    done = "done"
    escalated = "escalated"


class TaskReason(StrEnum):
    readers_disagree = "readers_disagree"
    ocr_too_unsure = "ocr_too_unsure"
    expert_hint = "expert_hint"


class Decision(StrEnum):
    accept_ocr = "accept_ocr"
    accept_model = "accept_model"
    correct = "correct"
    illegible = "illegible"


class HintType(StrEnum):
    context_note = "context_note"
    terminology = "terminology"
    transcription_fix = "transcription_fix"


class HintStatus(StrEnum):
    submitted = "submitted"
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    rejected = "rejected"
    published = "published"
    revoked = "revoked"


class EvidenceStatus(StrEnum):
    documentary = "documentary"
    tacit = "tacit"


class UploadStatus(StrEnum):
    open = "open"
    scanning = "scanning"
    committed = "committed"
    rejected = "rejected"
    expired = "expired"


class UploadMode(StrEnum):
    dossier = "dossier"
    bulk = "bulk"


class AppRole(StrEnum):
    reader = "DocAI.Reader"
    expert = "DocAI.Expert"
    steward = "DocAI.Steward"
    admin = "DocAI.Admin"
    uploader = "DocAI.Uploader"  # defined, unassigned in the MVP
    auditor = "DocAI.Auditor"  # defined, unassigned in the MVP


class GroupKind(StrEnum):
    reader = "reader"
    expert = "expert"
    steward = "steward"
    uploader = "uploader"
    restricted = "restricted"


class Capability(StrEnum):
    ask = "ask"
    review = "review"  # submit hints, settle review tasks
    approve = "approve"  # approve hints, restrict dossiers, escalated tasks
    upload = "upload"
