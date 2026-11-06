"""Model, conversion, clock and content-safety ports."""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from docai.contracts.artifacts import OcrResult
from docai.contracts.llm import VlmOutput
from docai.schemas.rows import ShieldResult


class OcrEngine(Protocol):
    def read(self, image: bytes, *, page_key: str, text_layer_pdf: bytes | None = None) -> OcrResult: ...


class VisionModel(Protocol):
    def transcribe(self, crop: bytes, *, lang_hint: str, line_key: str) -> VlmOutput:
        """Sees only the image. It is never given the OCR text (spec, Step 5)."""


class ChatModel(Protocol):
    def complete_json(self, role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        """`role` selects the deployment from settings: router, segmentation, metadata, verifier."""


class Embedder(Protocol):
    dimensions: int
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class DocumentConverter(Protocol):
    def to_pdf(self, data: bytes, filename: str) -> bytes:
        """DOC, DOCX or TXT to PDF with a text layer (Azure: LibreOffice in the job image)."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class ContentSafety(Protocol):
    def shield(self, *, question: str | None = None, documents: list[str] | None = None) -> ShieldResult:
        """Prompt Shields: user-prompt attacks in the question, planted instructions in documents."""
