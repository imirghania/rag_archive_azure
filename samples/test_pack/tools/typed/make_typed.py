"""Builds samples/test_pack/typed/: typed test documents as scanned PDF/TIFF (Pillow, 300 dpi), DOCX and TXT.
Run: uv run python samples/test_pack/tools/typed/make_typed.py   (deterministic, seed fixed)
No soffice here, so no digital-born PDF."""
from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import sys
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from content import DOSSIERS, H, P, T  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "typed"
SEED = 90
FD = Path("/usr/share/fonts/truetype/dejavu")
W, HT, MARGIN = 2480, 3508, 210  # A4 at 300 dpi
AR = re.compile(r"[؀-ۿ]")
NUM = re.compile(r"^[\d٠-٩.,٫٬%٪\s]+$")


def rtl_text(s: str) -> bool:
    """Right-to-left when the first letter is Arabic (digits count as the surrounding text)."""
    for ch in s:
        if AR.match(ch):
            return True
        if ch.isalpha():
            return False
    return False


# ------------------------------------------------------------------ scanned page
def font(lang: str, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = ("DejaVuSans" if lang != "en" else "DejaVuSerif") + ("-Bold" if bold else "") + ".ttf"
    return ImageFont.truetype(str(FD / name), size, layout_engine=ImageFont.Layout.RAQM)


def kw(s: str) -> dict:
    return {"direction": "rtl", "language": "ar"} if rtl_text(s) else {"direction": "ltr"}


def wrap(s: str, f: ImageFont.FreeTypeFont, maxw: int) -> list[str]:
    lines, cur = [], ""
    for w in s.split(" "):
        t = f"{cur} {w}".strip()
        if cur and f.getlength(t, **kw(s)) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + [cur]


def draw_text(d, s, f, x0, x1, y, align="start", fill=0):
    """Draws one line between x0 and x1; `align` is left, right, or start (by text direction)."""
    w = f.getlength(s, **kw(s))
    right = align == "right" or (align == "start" and rtl_text(s))
    d.text(((x1 - w) if right else x0, y), s, font=f, fill=fill, **kw(s))


def draw_table(d, t: T, y: int, lang: str) -> int:
    f, fb, pad = font(lang, 38), font(lang, 38, True), 14
    lh = 38 * 1.45
    n = len(t.header)
    wt = [min(max(len(r[i]) for r in [t.header] + t.rows), 30) + 6 for i in range(n)]
    cw = [int((W - 2 * MARGIN) * w / sum(wt)) for w in wt]
    rtl = rtl_text(t.header[0]) if t.rtl is None else t.rtl
    xs, x = [], MARGIN
    for c in (cw[::-1] if rtl else cw):
        xs.append((x, x + c))
        x += c
    if rtl:
        xs = xs[::-1]  # logical column 0 at the right edge
    top = y
    for ri, row in enumerate([t.header] + t.rows):
        bold = ri == 0 or ri > len(t.rows) - t.foot
        ff = fb if bold else f
        cells = [wrap(c, ff, cw[i] - 2 * pad) if c else [""] for i, c in enumerate(row)]
        h = int(max(len(c) for c in cells) * lh + 2 * pad)
        if ri == 0:
            d.rectangle((MARGIN, y, W - MARGIN, y + h), fill=222)
        for i, lines in enumerate(cells):
            a, b = xs[i]
            numeric = bool(NUM.match(row[i])) and ri > 0
            for k, ln in enumerate(lines):
                if numeric:
                    al = "left" if rtl else "right"
                else:
                    al = "right" if (rtl or rtl_text(ln)) else "left"
                draw_text(d, ln, ff, a + pad, b - pad, y + pad + k * lh, al)
        y += h
        d.line((MARGIN, y, W - MARGIN, y), fill=90, width=2)
    for a, b in xs:
        d.line((a, top, a, y), fill=90, width=2)
    d.line((xs[-1][1] if not rtl else xs[0][1], top, xs[-1][1] if not rtl else xs[0][1], y), fill=90, width=2)
    d.line((MARGIN, top, W - MARGIN, top), fill=90, width=2)
    return y


def render_page(doc) -> Image.Image:
    img = Image.new("L", (W, HT), 255)
    d = ImageDraw.Draw(img)
    lang, body = doc.lang, 44
    y = 200
    d.text((MARGIN, y), doc.title, font=font(lang, 68, True), fill=0)
    y += 110
    d.text((MARGIN, y), f"Ref: {doc.ref}", font=font(lang, 44), fill=0)
    y += 80
    d.line((MARGIN, y, W - MARGIN, y), fill=0, width=4)
    y += 60
    for b in doc.blocks:
        if isinstance(b, T):
            y = draw_table(d, b, y, lang) + 50
            continue
        f = font(lang, body + (4 if isinstance(b, H) else 0), isinstance(b, H))
        for ln in wrap(b.text, f, W - 2 * MARGIN):
            draw_text(d, ln, f, MARGIN, W - MARGIN, y)
            y += int(f.size * 1.6)
        y += 26 if isinstance(b, H) else 38
    assert y < HT - MARGIN, f"{doc.ref} overflows the page ({y})"
    return img


def scan(img: Image.Image, rng: random.Random) -> Image.Image:
    """Grey paper tone, mild noise, slight rotation (0.3 to 0.8 degrees), light blur."""
    img = ImageChops.multiply(img, Image.new("L", img.size, 236))
    noise = Image.frombytes("L", img.size, rng.randbytes(img.size[0] * img.size[1])).point(lambda v: v // 14)
    img = ImageChops.add(img, noise, 1, -9)
    ang = rng.uniform(0.3, 0.8) * rng.choice([-1, 1])
    img = img.rotate(ang, resample=Image.BICUBIC, fillcolor=205)
    return img.filter(ImageFilter.GaussianBlur(0.6))


# ------------------------------------------------------------------ docx
def add_runs(par, text, bold=False, size=11):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt
    for part in re.split(r"([؀-ۿ][؀-ۿ\s،.,%٪٫٬\d]*)", text):
        if not part:
            continue
        r = par.add_run(part)
        r.bold, r.font.size, r.font.name = bold, Pt(size), "Arial"
        rpr = r._r.get_or_add_rPr()
        rpr.find(qn("w:rFonts")).set(qn("w:cs"), "Arial")  # Arabic-capable font for complex-script runs
        if AR.search(part):
            rpr.append(OxmlElement("w:rtl"))
            sz = OxmlElement("w:szCs")
            sz.set(qn("w:val"), str(size * 2))
            rpr.append(sz)


def bidi(par):
    from docx.oxml import OxmlElement
    par._p.get_or_add_pPr().append(OxmlElement("w:bidi"))


def make_docx(doc, path: Path):
    from docx import Document
    from docx.oxml import OxmlElement
    d = Document()
    add_runs(d.add_paragraph(), doc.title, True, 16)
    add_runs(d.add_paragraph(), f"Ref: {doc.ref}")
    for b in doc.blocks:
        if isinstance(b, T):
            rtl = rtl_text(b.header[0]) if b.rtl is None else b.rtl
            tbl = d.add_table(rows=1 + len(b.rows), cols=len(b.header))
            tbl.style = "Table Grid"
            if rtl:
                tbl._tbl.tblPr.append(OxmlElement("w:bidiVisual"))
            for ri, row in enumerate([b.header] + b.rows):
                for ci, c in enumerate(row):
                    p = tbl.cell(ri, ci).paragraphs[0]
                    if rtl_text(c):
                        bidi(p)
                    add_runs(p, c, ri == 0 or ri > len(b.rows) - b.foot)
            d.add_paragraph()
        else:
            p = d.add_paragraph()
            if rtl_text(b.text):
                bidi(p)
            add_runs(p, b.text, isinstance(b, H), 13 if isinstance(b, H) else 11)
    d.save(path)


def make_txt(doc, path: Path):
    out = [doc.title, f"Ref: {doc.ref}", ""]
    for b in doc.blocks:
        if isinstance(b, T):
            out += [" | ".join(r) for r in [b.header] + b.rows] + [""]
        else:
            out += [b.text, ""]
    path.write_text("\n".join(out), encoding="utf-8")


# ------------------------------------------------------------------ dossiers
def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*-C9?-S?-F????"):  # questions.md is hand-written and stays
        shutil.rmtree(old)
    rng = random.Random(SEED)
    rows = []
    for did, dept, lang, scan_ext, items in DOSSIERS:
        dd = OUT / did
        dd.mkdir(parents=True)
        files = []
        frames = [scan(render_page(doc), rng) for doc, f in items if f == "scan"]
        sname = f"scan_001.{scan_ext}"
        if scan_ext == "pdf":
            frames[0].save(dd / sname, "PDF", resolution=300.0, save_all=True, append_images=frames[1:], quality=70,
                           creationDate=time.gmtime(1780272000), modDate=time.gmtime(1780272000))
        else:  # JPEG-in-TIFF keeps the grey-noise pages small
            frames[0].save(dd / sname, save_all=True, append_images=frames[1:], compression="jpeg", quality=70, dpi=(300, 300))
        files.append({"name": sname, "bytes": (dd / sname).stat().st_size, "sha256": sha(dd / sname), "pages": len(frames)})
        for doc, f in items:
            if f == "scan":
                rows.append((sname, did, doc, "scanned " + scan_ext.upper() + f", page {[x for x, ff in items if ff == 'scan'].index(doc) + 1}"))
                continue
            name = f"{doc.ref}.{f}"
            (make_docx if f == "docx" else make_txt)(doc, dd / name)
            files.append({"name": name, "bytes": (dd / name).stat().st_size, "sha256": sha(dd / name)})
            rows.append((name, did, doc, f.upper()))
        (dd / "dossier.json").write_text(json.dumps({
            "schema": 1, "dossier_id": did, "source": "upload", "upload_id": None, "uploaded_by": None,
            "segmentation": "auto", "files": files}, indent=1))
    write_readme(rows)
    print(f"{len(rows)} documents in {len(DOSSIERS)} dossiers -> {OUT}")


LANG = {"en": "English", "ar": "Arabic", "mixed": "Arabic + English"}
UPLOAD = {"scanned": "Upload the whole scan file", "DOCX": "Upload as a Word file", "TXT": "Upload as a text file"}


def write_readme(rows) -> None:
    lines = ["| File | Dossier | Dept | Language | Format | Document (Ref) | What it contains | Upload as |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for fname, did, doc, fmt in rows:
        up = UPLOAD["scanned"] if fmt.startswith("scanned") else UPLOAD[fmt]
        lines.append(f"| `{fname}` | `{did}` | {doc.dept} | {LANG[doc.lang]} | {fmt} | {doc.title.title()} (`{doc.ref}`) | {doc.what} | {up}; dossier ID `{did}` |")
    (OUT / "README.md").write_text(README.replace("@@TABLE@@", "\n".join(lines)), encoding="utf-8")


README = """# Typed test pack

Synthetic, typed (no handwriting) documents for the RAG system: 6 dossiers, 21 documents, Finance and HR, English, Arabic and mixed Arabic + English. All organisations, people and numbers are invented and consistent with each other (for example the rent in the lease equals the rent debited in the bank statement, and the payroll total equals the payroll debit).

Regenerate everything (deterministic, seed fixed): `uv run python samples/test_pack/tools/typed/make_typed.py`. The generator rebuilds the dossier folders and this README; `questions.md` is hand-written and is left alone.

Each dossier folder has the layout of `samples/templates/filled/`: the files to upload plus `dossier.json` (the manifest; never select `dossier.json` in the upload dialog, the server refuses that name).

## Files

@@TABLE@@

## How the pages are made

- Every page has a CAPITAL-LETTER title as its first line and a `Ref:` line second, because the system cuts a dossier into documents with those two cues. The title and `Ref:` lines are in Latin letters even on Arabic documents. Each document is one page.
- Scans: A4 at 300 dpi, grey paper tone, mild noise, rotation of 0.3 to 0.8 degrees, light blur. PDF files in the `C90` dossiers, JPEG-compressed TIFF in the `C91` dossiers. One file per dossier (`scan_001.*`) holds the scanned documents in order.
- DOCX: Arial runs, right-to-left paragraphs and tables (`w:bidi`, `w:bidiVisual`) for Arabic.
- TXT: UTF-8, tables as `a | b | c`.
- No digital-born PDF: `soffice` is not installed here, and no PDF library is.
- Arabic is shaped and ordered by Pillow with Raqm (HarfBuzz and FriBiDi).

## How to upload

Web app (local dev server or the Azure deployment):

1. Sign in as **Sara** (Expert, uploads). Open **Upload**.
2. Choose the department that matches the dossier ID prefix (`FIN` or `HR`), mode **By dossier**, type the dossier ID, select all files of that folder except `dossier.json`, **Check files**, **Confirm and upload**.
3. Wait until the dossier shows `completed`.
4. Ask questions as **Layla** (reads Finance: she must see only `FIN-*` dossiers) or **Huda** (reads HR: only `HR-*` dossiers). See `questions.md`.

Note: the local runtime reads pages from canned fixtures, not from a real OCR, so these new files only process end to end on the Azure deployment (or after fixtures are made for them). The DOCX and TXT files need no OCR.
"""

if __name__ == "__main__":
    main()
