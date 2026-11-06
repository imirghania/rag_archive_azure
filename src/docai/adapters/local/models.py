"""Local fakes for the model ports. They are deterministic, so the pipeline tests are repeatable.

* FixtureOcr and FixtureVision read the canned results that docai.devtools.samples writes next to the sample scans.
* ScriptedChat answers the structured prompts with simple rules (it stands in for the models, it is not one).
* HashEmbedder gives real lexical similarity from hashed words, so retrieval tests mean something."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

from pydantic import BaseModel

from docai.contracts import keys
from docai.contracts.artifacts import OcrResult
from docai.contracts.llm import MetadataOutput, SegmentationVerdict, VlmOutput

_TOKEN = re.compile(r"[a-z0-9؀-ۿ]+")
_ARABIC = re.compile(r"[؀-ۿ]")


class FixtureOcr:
    def __init__(self, fixtures_dir: Path) -> None:
        self.dir = Path(fixtures_dir)

    def read(self, image: bytes, *, page_key: str, text_layer_pdf: bytes | None = None) -> OcrResult:
        if text_layer_pdf is not None:
            return self._from_text_layer(text_layer_pdf)
        ref = keys.PageRef.parse(page_key)
        path = self.dir / ref.dossier_id / f"p{ref.page_no:03d}.ocr.json"
        if not path.exists():
            raise FileNotFoundError(f"no OCR fixture for {page_key}: {path}")
        return OcrResult.model_validate_json(path.read_text(encoding="utf-8"))


    @staticmethod
    def _from_text_layer(pdf_bytes: bytes) -> OcrResult:
        """One line per line of text in the layer, with its box in pixels at 300 dpi and confidence 1.0."""
        import pypdfium2 as pdfium

        from docai.contracts.artifacts import Box, OcrLine
        page = pdfium.PdfDocument(pdf_bytes)[0]
        w, h = page.get_size()
        scale = 300 / 72
        text = page.get_textpage()
        lines = []
        for i, raw in enumerate([x for x in text.get_text_range().replace("\r", "").split("\n") if x.strip()], start=1):
            y0 = round((72 + (i - 1) * 15) * scale)
            lines.append(OcrLine(id=f"L{i}", text=raw.strip(), box=Box(x0=round(56 * scale), y0=y0, x1=round(min(w - 40, 56 + 6.2 * len(raw)) * scale), y1=y0 + round(13 * scale)),
                                conf=1.0, style="printed", lang="ar" if _ARABIC.search(raw) else "en", from_text_layer=True))
        return OcrResult(engine="text-layer", page_width=round(w * scale), page_height=round(h * scale), lines=lines)


class FixtureVision:
    def __init__(self, fixtures_dir: Path) -> None:
        self.dir = Path(fixtures_dir)
        self.calls: list[str] = []  # line keys, so tests can assert what the second reader was asked

    def transcribe(self, crop: bytes, *, lang_hint: str, line_key: str) -> VlmOutput:
        self.calls.append(line_key)
        ref = keys.LineRef.parse(line_key)
        path = self.dir / ref.page.dossier_id / f"p{ref.page.page_no:03d}.vlm.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return VlmOutput.model_validate(data[ref.line_id])


_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                    "september", "october", "november", "december"], start=1)}


def _iso_date(text: str) -> str | None:
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if not m or m[2].lower() not in _MONTHS:
        return None
    return f"{m[3]}-{_MONTHS[m[2].lower()]:02d}-{int(m[1]):02d}"


class ScriptedChat:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def complete_json(self, role: str, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        self.calls.append(role)
        if role == "segmentation":
            return self._segmentation(user)
        if role == "metadata":
            return self._metadata(user)
        if role == "router":
            return self._router(user)
        if role == "verifier":
            return self._verifier(user)
        raise NotImplementedError(f"ScriptedChat has no script for role {role}")

    _STOP = {"how", "much", "was", 
            "what", "the", "for", "did", 
            "we", "is", "a", "of", "to", 
            "and", "who", "in", "me", "write", 
            "about", "all", "list"}
    _AR_TO_EN = {
        "كم المبلغ المعتمد لتجديد عقد إيجار القطعة 118؟": "approved amount Plot 118 lease renewal"
        }  # the scripted router cannot translate

    @classmethod
    def _router(cls, user: str):
        from docai.contracts.llm import RouterOutput
        q = json.loads(user)["question"]
        ar = bool(_ARABIC.search(q))
        if re.search(r"\b(poem|joke|story)\b", q, re.I):
            return RouterOutput(language="en", intent="out_of_scope")
        words = [w for w in _TOKEN.findall(q.lower()) if w not in cls._STOP]
        en = cls._AR_TO_EN.get(q, "" if ar else " ".join(words))
        return RouterOutput(language="ar" if ar else "en", intent="doc_lookup", query_en=en, query_ar=q if ar else "")

    @staticmethod
    def _verifier(user: str):
        from docai.contracts.llm import ClaimVerdict, VerifierOutput
        out = []
        for c in json.loads(user)["claims"]:
            claim_words = {w for w in _TOKEN.findall(c["claim"].lower()) if len(w) > 3}
            line_words = {w for ln in c["lines"] for w in _TOKEN.findall(ln["text"].lower())}
            ok = not claim_words or len(claim_words & line_words) / len(claim_words) >= 0.6
            out.append(ClaimVerdict(claim_id=c["claim_id"], verdict="supported" if ok else "unsupported", missing="" if ok else "claim words not in the cited lines"))
        return VerifierOutput(verdicts=out)

    @staticmethod
    def _segmentation(user: str) -> SegmentationVerdict:
        payload = json.loads(user)
        first_b = payload["B"][0]
        return SegmentationVerdict(verdict="same", 
                                evidence=[
                                    {
                                        "page": "B", 
                                        "line_id": first_b["line_id"], 
                                        "quote": first_b["text"]
                                        }
                                    ]
                                )

    @staticmethod
    def _metadata(user: str) -> MetadataOutput:
        lines = [(m[1], m[2]) for m in (re.match(r"^(p\d+/L\d+): (.*)$", ln) for ln in user.splitlines()) if m]
        out: dict[str, dict] = {}
        for key, text in lines:
            if "[unverified" in text:
                continue  # doubtful lines never feed the date or the reference (prompt rule)
            if "date" not in out and (m := re.match(r"^Date:\s*(.+)$", text)) and (iso := _iso_date(m[1])):
                out["date"] = {"value": iso, "evidence": key}
            if "reference" not in out and (m := re.match(r"^(?:Ref:|Contract No\.)\s*(\S+)", text)):
                out["reference"] = {"value": m[1], "evidence": key}
            if "subject" not in out and (m := re.match(r"^Subject:\s*(.+)$", text)):
                out["subject"] = {"value": m[1].strip(), "evidence": key}
        for key, text in lines:
            up = text.upper()
            for needle, label in (("MEMORANDUM", "internal_memo"), ("INVOICE", "invoice"), ("LEASE AGREEMENT", "contract"),
                                  ("TREASURY NOTE", "treasury_note"), ("COMPLAINT", "complaint"), ("HUMAN RESOURCES", "hr_notice")):
                if needle in up and "doc_type" not in out:
                    out["doc_type"] = {"value": label, "evidence": key}
        if "doc_type" not in out and any(t.startswith("Dear") for _, t in lines):
            out["doc_type"] = {"value": "letter", "evidence": next(k for k, t in lines if t.startswith("Dear"))}
        langs = ["en"] + (["ar"] if any(_ARABIC.search(t) for _, t in lines) else [])
        return MetadataOutput.model_validate({**out, "languages": langs})


class HashEmbedder:
    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dimensions
            for tok in _TOKEN.findall(t.lower()):
                h = int.from_bytes(hashlib.md5(tok.encode()).digest()[:8], "big")
                v[h % self.dimensions] += 1.0 if (h >> 63) & 1 else -1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


class RuleShield:
    """Stands in for Prompt Shields: flags the obvious planted-instruction phrases of the test material."""

    PATTERNS = ("ignore your instructions", "ignore previous instructions", "ignore all previous", "disregard the above")

    def shield(self, *, question: str | None = None, documents: list[str] | None = None):
        from docai.ports import ShieldResult

        def hit(s: str) -> bool:
            return any(p in s.lower() for p in self.PATTERNS)

        return ShieldResult(question is not None and hit(question), [hit(d) for d in documents or []])
