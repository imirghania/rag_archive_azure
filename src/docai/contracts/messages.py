"""The message envelope, payload shapes and the queue catalogue (spec, Service Bus)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .enums import Priority


class Envelope(BaseModel):
    type: str
    schema_: int = Field(default=1, alias="schema", serialization_alias="schema")
    subject: str
    dossier_id: str | None = None
    revision: int | None = None
    department: str
    priority: Priority = Priority.online
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True, "extra": "ignore"}

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True)

    @classmethod
    def from_json(cls, text: str | bytes) -> Envelope:
        return cls.model_validate_json(text)


@dataclass(frozen=True)
class QueueSpec:
    name: str
    sessions: bool = False
    dup_window: str = "PT1H"  # ISO 8601 duration
    max_delivery: int = 5


QUEUES: dict[str, QueueSpec] = {
    q.name: q
    for q in [
        QueueSpec("q-intake", dup_window="P1D"),
        QueueSpec("q-upload-commit"),
        QueueSpec("q-preprocess"),
        QueueSpec("q-digital"),
        QueueSpec("q-ocr-online"),
        QueueSpec("q-handwriting-online"),
        QueueSpec("q-reconcile"),
        QueueSpec("q-segment"),
        QueueSpec("q-metadata"),
        QueueSpec("q-chunk", sessions=True),
        QueueSpec("q-index", sessions=True),
        QueueSpec("q-post-review", sessions=True),
        QueueSpec("q-hint-events"),
    ]
}

TOPIC = "t-docai-events"
SUBSCRIPTION_NOTIFY = "notify"
NOTIFY_TYPES = (
    "hint.published",
    "hint.rejected",
    "hint.revoked",
    "review.escalated",
    "dossier.failed",
    "dossier.partial",
    "upload.rejected",
)
EVENT_TYPES = ("document.indexed", "document.removed", *NOTIFY_TYPES)

# message type -> queue
ROUTES: dict[str, str] = {
    "dossier.received": "q-intake",
    "dossier.reprocess.requested": "q-intake",
    "upload.commit.requested": "q-upload-commit",
    "dossier.preprocess.requested": "q-preprocess",
    "file.convert.requested": "q-digital",
    "page.ocr.requested": "q-ocr-online",
    "page.second-read.requested": "q-handwriting-online",
    "page.reconcile.requested": "q-reconcile",
    "dossier.segment.requested": "q-segment",
    "document.metadata.requested": "q-metadata",
    "document.chunk.requested": "q-chunk",
    "document.index.requested": "q-index",
    "document.acl.changed": "q-index",
    "chunk.flagged": "q-index",
    "review.decided": "q-post-review",
    "hint.changed": "q-hint-events",
    "dossier.acl.changed": "q-hint-events",
}


def destination_of(message_type: str) -> str:
    """A queue name, or the topic for an event."""
    if message_type in ROUTES:
        return ROUTES[message_type]
    if message_type in EVENT_TYPES:
        return TOPIC
    raise ValueError(f"unknown message type: {message_type}")


def session_of(queue: str, document_id: str | None) -> str | None:
    return document_id if QUEUES.get(queue, QueueSpec(queue)).sessions else None


# payloads (validated by the consumer; the envelope stays generic)
class DossierReceived(BaseModel):
    source: Literal["upload"] = "upload"
    manifest: str  # path of dossier.json inside the `raw` container
    manifest_hash: str
    upload_id: str | None = None


class ReprocessRequested(BaseModel):
    requested_by: str
    reason: str = ""
    from_revision: int


class UploadCommitRequested(BaseModel):
    upload_id: str
    attempt: int = 1


class FileRef(BaseModel):
    name: str
    location: Literal["raw", "extracted"] = "raw"


class PreprocessRequested(BaseModel):
    files: list[FileRef]
    raw_dir: str  # where the revision's original files live in `raw` (a reprocess reads the folder of the first upload)


class ConvertRequested(BaseModel):
    name: str
    raw_dir: str


class PageOcrRequested(BaseModel):
    page_no: int
    page_dir: str
    image: str = "page.png"
    text_layer: bool = False


class SecondReadLine(BaseModel):
    line_id: str
    crop: str
    lang_hint: str = "en"


class SecondReadRequested(BaseModel):
    page_no: int
    page_dir: str
    page_image_sha256: str
    lines: list[SecondReadLine]  # deliberately no OCR text


class ReconcileRequested(BaseModel):
    page_no: int
    page_dir: str
    second_reads: dict[str, str] = Field(default_factory=dict)
    expected_second_reads: int = 0


class SegmentRequested(BaseModel):
    pass


class MetadataRequested(BaseModel):
    document_id: str


class ChunkRequested(BaseModel):
    document_id: str
    version: int


class IndexRequested(BaseModel):
    document_id: str
    version: int
    parquet: str


class AclChanged(BaseModel):
    acl_version: int


class ChunkFlagged(BaseModel):
    chunk_id: str
    injection_suspect: bool
    flag_source: str = "prompt_shields"


class ReviewDecided(BaseModel):
    task_id: int
    decision: str
    text: str | None = None
    decision_file: str
    document_id: str


class HintChanged(BaseModel):
    status: str
    version: int
    row_version: int


PAYLOADS: dict[str, type[BaseModel]] = {
    "dossier.received": DossierReceived,
    "dossier.reprocess.requested": ReprocessRequested,
    "upload.commit.requested": UploadCommitRequested,
    "dossier.preprocess.requested": PreprocessRequested,
    "file.convert.requested": ConvertRequested,
    "page.ocr.requested": PageOcrRequested,
    "page.second-read.requested": SecondReadRequested,
    "page.reconcile.requested": ReconcileRequested,
    "dossier.segment.requested": SegmentRequested,
    "document.metadata.requested": MetadataRequested,
    "document.chunk.requested": ChunkRequested,
    "document.index.requested": IndexRequested,
    "document.acl.changed": AclChanged,
    "chunk.flagged": ChunkFlagged,
    "review.decided": ReviewDecided,
    "hint.changed": HintChanged,
    "dossier.acl.changed": AclChanged,
}


def parse_payload(env: Envelope) -> BaseModel:
    model = PAYLOADS.get(env.type)
    if model is None:
        raise ValueError(f"no payload contract for {env.type}")
    return model.model_validate(env.payload)
