"""OcrEngine adapter: Azure AI Document Intelligence, Layout model. Lines carry text, a polygon in the pixels of our 300 dpi
page image, a confidence (the mean of the line's words) and a handwriting flag (from the document styles). If the account
has Content Understanding instead, a second adapter behind the same port replaces this one; nothing else changes."""
from __future__ import annotations

import io
import re
from typing import Any

from PIL import Image

from docai.contracts.artifacts import Box, OcrLine, OcrResult

_ARABIC = re.compile(r"[؀-ۿ]")


def _overlap(a_off: int, a_len: int, b_off: int, b_len: int) -> bool:
    return a_off < b_off + b_len and b_off < a_off + a_len


def to_ocr_result(result: Any, page_width: int, 
                page_height: int, *, from_text_layer: bool, 
                engine: str = "document-intelligence-layout") -> OcrResult:
    """Pure conversion of an AnalyzeResult (or anything shaped like one) into our contract."""
    page = result.pages[0]
    scale_x, scale_y = page_width / page.width, page_height / page.height  # PDF pages are in inches, images in pixels
    handwritten = [(s.offset, s.length) 
                for st in (getattr(result, "styles", None) or []) 
                if getattr(st, "is_handwritten", False) for s in st.spans
                ]
    words = getattr(page, "words", None) or []
    lines = []
    for i, ln in enumerate(page.lines or [], start=1):
        span = ln.spans[0] if ln.spans else None
        xs, ys = ln.polygon[0::2], ln.polygon[1::2]
        in_line = [w.confidence for w in words if span and w.span and _overlap(span.offset, span.length, w.span.offset, w.span.length)]  # a word has one `span`, a line has `spans` (D51)
        conf = ( round(sum(in_line) / len(in_line), 3) 
                if in_line else (1.0 if from_text_layer else 0.0) )
        hand = bool(span) and any(
            _overlap(span.offset, span.length, o, n) for o, n in handwritten
            )
        lines.append(OcrLine(
            id=f"L{i}", text=ln.content, conf=min(max(conf, 0.0), 1.0), 
            style="handwritten" if hand else "printed", 
            lang="ar" if _ARABIC.search(ln.content) else "en",
            from_text_layer=from_text_layer, 
            box=Box(x0=round(min(xs) * scale_x), 
                    y0=round(min(ys) * scale_y), 
                    x1=round(max(xs) * scale_x), 
                    y1=round(max(ys) * scale_y))
            ))
    return OcrResult(engine=engine, page_width=page_width,
                    page_height=page_height, lines=lines)


class DocumentIntelligenceOcr:
    def __init__(self, endpoint: str, 
                credential: Any = None, *, client: Any = None) -> None:
        from azure.identity import DefaultAzureCredential

        if client is None:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            client = DocumentIntelligenceClient(endpoint, 
                                                credential or DefaultAzureCredential())
        self.client = client

    def read(self, image: bytes, *, page_key: str, 
            text_layer_pdf: bytes | None = None) -> OcrResult:
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

        w, h = Image.open(io.BytesIO(image)).size
        source = text_layer_pdf if text_layer_pdf is not None else image  # a page with a text layer goes in as its one-page PDF
        poller = self.client.begin_analyze_document("prebuilt-layout", 
                                                    AnalyzeDocumentRequest(bytes_source=source))
        return to_ocr_result(poller.result(), w, h, 
                            from_text_layer=text_layer_pdf is not None)
