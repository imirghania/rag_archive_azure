"""Structured outputs of the models. Each is also the JSON schema sent as `response_format`."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .artifacts import Evidenced


class VlmOutput(BaseModel):
    text: str
    lang: Literal["en", "ar", "mixed", "other"] = "en"
    uncertain: list[str] = Field(default_factory=list)


class RouterFilters(BaseModel):
    doc_type: str | None = None
    year: int | None = None
    reference: str | None = None
    dossier_id: str | None = None


class RouterOutput(BaseModel):
    language: Literal["en", "ar"]
    intent: Literal["doc_lookup", "summary", "follow_up", "out_of_scope"]
    query_en: str = ""
    query_ar: str = ""
    filters: RouterFilters = Field(default_factory=RouterFilters)


class SegmentationEvidence(BaseModel):
    page: Literal["A", "B"]
    line_id: str
    quote: str


class SegmentationVerdict(BaseModel):
    verdict: Literal["same", "new", "unsure"]
    evidence: list[SegmentationEvidence] = Field(default_factory=list)


class MetadataOutput(BaseModel):
    doc_type: Evidenced | None = None
    date: Evidenced | None = None
    reference: Evidenced | None = None
    subject: Evidenced | None = None
    languages: list[Literal["en", "ar"]] = Field(default_factory=list)


class ClaimVerdict(BaseModel):
    claim_id: int
    verdict: Literal["supported", "partial", "unsupported"]
    missing: str = ""


class VerifierOutput(BaseModel):
    verdicts: list[ClaimVerdict]
