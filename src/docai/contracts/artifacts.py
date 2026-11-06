"""Stored artifacts: what one module writes to ADLS and another reads (spec, Workflow 1).

Every model carries `schema`. A contract changes only by adding optional fields, or by a new
schema number that readers accept next to the old one."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .enums import Decision, TrustTier


class Contract(BaseModel):
    # Readers ignore fields added by newer writers; `schema` is serialized under that name.
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    schema_: int = Field(default=1, alias="schema", serialization_alias="schema")


class Box(BaseModel):
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    def overlap_y(self, other: Box) -> int:
        return max(0, min(self.y1, other.y1) - max(self.y0, other.y0))


Style = Literal["printed", "handwritten"]
Route = Literal["accept", "second_read"]
Placement = Literal["main", "right_margin", "left_margin", "top_margin", "bottom_margin", "inline"]


# preprocess.json
class PreprocessInfo(Contract):
    source: str
    frame: int
    deskew_deg: float = 0.0
    dpi: int = 300
    text_layer: bool = False
    width: int = 0
    height: int = 0
    page_image_sha256: str = ""


# ocr.json (the OCR engine port returns this)
class OcrLine(BaseModel):
    id: str  # L17
    text: str
    box: Box
    conf: float = Field(ge=0, le=1)
    style: Style = "printed"
    lang: str = "en"
    from_text_layer: bool = False


class OcrResult(Contract):
    engine: str
    page_width: int
    page_height: int
    lines: list[OcrLine]


# triage.json
class TriageLine(BaseModel):
    id: str
    style: Style
    conf: float
    route: Route
    lang: str = "en"
    crop: str | None = None  # crops/L17.png
    crop_box: Box | None = None
    crop_sha256: str | None = None


class Triage(Contract):
    page: str
    page_image_sha256: str
    lines: list[TriageLine]

    def flagged(self) -> list[TriageLine]:
        return [t for t in self.lines if t.route == "second_read"]


# Lnn.vlm.json
class VlmReading(Contract):
    line_key: str
    text: str
    lang: str = "en"
    uncertain: list[str] = Field(default_factory=list)
    model: str
    crop_sha256: str
    read_at: datetime
    mode: Literal["online", "batch"] = "online"


# Lnn.readings.json (for the reviewer)
class ReadingEntry(BaseModel):
    engine: str  # ocr | second_reader
    text: str
    conf: float | None = None


class Readings(Contract):
    line_key: str
    readings: list[ReadingEntry]


# lines.vN.json
class Line(BaseModel):
    id: str
    text: str
    tier: TrustTier
    style: Style
    box: Box
    lang: str = "en"
    conf: float | None = None
    source: Literal["ocr", "second_reader", "text_layer", "human", "placeholder"] = "ocr"
    candidates: list[str] = Field(default_factory=list)  # competing readings of an unverified line
    anchor: str | None = None  # paragraph a margin note is attached to (P3)
    placement: Placement = "main"
    paragraph: str | None = None  # paragraph this line belongs to (P3)
    decision_file: str | None = None


class LinesFile(Contract):
    page_key: str
    page_no: int
    version: int = 1
    page_width: int = 0
    page_height: int = 0
    page_image_sha256: str = ""
    lines: list[Line]

    def line(self, line_id: str) -> Line:
        for ln in self.lines:
            if ln.id == line_id:
                return ln
        raise KeyError(line_id)


# Lnn.decision.<lease>.json
class DecisionFile(Contract):
    task_id: int
    line_key: str
    decision: Decision
    text: str | None = None
    tier: TrustTier
    by_oid: str
    by_name: str = ""
    at: datetime
    lease_token: str


# documents.json and metadata.json
class DocumentSpan(BaseModel):
    document_id: str
    first_page: int
    last_page: int
    title: str = ""
    cues: str = ""
    source_files: list[str] = Field(default_factory=list)
    has_gaps: bool = False


class DocumentsFile(Contract):
    dossier_key: str
    segmentation: Literal["auto", "per_file"] = "auto"
    documents: list[DocumentSpan]


class Evidenced(BaseModel):
    value: str
    evidence: str  # p12/L4: Date: 27 February 2008


class Catalog(BaseModel):
    department: str
    cabinet: str | None = None
    shelf: str | None = None
    section: str | None = None


class Metadata(Contract):
    document_id: str
    catalog: Catalog
    doc_type: Evidenced | None = None
    date: Evidenced | None = None
    reference: Evidenced | None = None
    subject: Evidenced | None = None
    languages: list[str] = Field(default_factory=list)
    min_trust: TrustTier = TrustTier.human_verified
    has_gaps: bool = False


# chunk record (Parquet row and index document)
class ChunkRecord(Contract):
    chunk_id: str
    document_id: str
    dossier_id: str
    revision: int
    version: int
    department: str
    text: str
    pages: list[int]
    line_refs: list[str]  # p014/L17
    trust_tiers: dict[str, TrustTier]
    min_trust: TrustTier
    min_trust_rank: int
    acl_groups: list[str]
    doc_type: str | None = None
    doc_date: str | None = None
    reference: str | None = None
    subject: str | None = None
    language: str = "en"
    injection_suspect: bool = False
    text_vector: list[float] = Field(default_factory=list)


class NoteRecord(Contract):
    """An entry of the `notes` index: one published hint."""

    hint_id: str
    department: str
    hint_type: str
    text: str
    acl_groups: list[str]
    scope_dossier_ids: list[str] = Field(default_factory=list)
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    evidence_status: str = "documentary"
    author: str = ""
    approved_by: str = ""
    approved_at: datetime | None = None
    review_by: str | None = None
    text_vector: list[float] = Field(default_factory=list)


# dossier.json (the manifest)
class ManifestFile(BaseModel):
    name: str
    bytes: int
    sha256: str
    pages: int | None = None


class Manifest(Contract):
    dossier_id: str
    source: Literal["upload"] = "upload"
    upload_id: str | None = None
    uploaded_by: str | None = None
    segmentation: Literal["auto", "per_file"] = "auto"
    files: list[ManifestFile]
