"""A pure-Python DOCX/TXT to PDF converter for tests: it writes a one-font PDF with a real text layer, as LibreOffice would
(Latin text only). The Azure adapter runs LibreOffice in the job image."""
from __future__ import annotations

import io
import textwrap
import zipfile
from xml.etree import ElementTree as ET

LINES_PER_PAGE, WRAP = 48, 88


def _paragraphs(data: bytes, filename: str) -> list[str]:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "txt":
        return data.decode("utf-8", errors="replace").splitlines()
    if ext == "docx":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        return ["".join(t.text or "" for t in p.iter(f"{ns}t")) for p in root.iter(f"{ns}p")]
    raise ValueError(f"the local converter cannot read .{ext}")


def _escape(s: str) -> str:
    return (s.encode("latin-1", errors="replace")
            .decode("latin-1").replace("\\", "\\\\")
            .replace("(", "\\(").replace(")", "\\)"))


class PurePdfConverter:
    def to_pdf(self, data: bytes, filename: str) -> bytes:
        lines = [w for para in _paragraphs(data, filename) 
                for w in (textwrap.wrap(para, WRAP) or [""])]
        pages = [lines[i:i + LINES_PER_PAGE] 
                for i in range(0, max(len(lines), 1), LINES_PER_PAGE)] or [[]]
        objs: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", 
                            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
        kids = []
        for pg in pages:
            stream = "BT /F1 11 Tf 56 790 Td 15 TL\n" + "\n".join(f"({_escape(l)}) '" for l in pg) + "\nET"
            content = len(objs) + 2
            kids.append(f"{len(objs) + 1} 0 R")
            objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content} 0 R >>".encode())
            objs.append(f"<< /Length {len(stream.encode('latin-1', 'replace'))} >>\nstream\n{stream}\nendstream".encode("latin-1", "replace"))
        objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()
        out, offsets = bytearray(b"%PDF-1.4\n"), []
        for i, o in enumerate(objs, start=1):
            offsets.append(len(out))
            out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
        out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        return bytes(out)
