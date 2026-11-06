"""PREVIEW_*.png: the prepared sheets with SIMULATED handwriting (existing helpers in docai.devtools.samples).
Only to show the intended look. Not for upload. Run make_paper.py first.
Run: uv run python samples/test_pack/tools/handwritten/make_preview.py"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

from paperlib import cpl_for, wrap_lines
from texts_data import TEXTS

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from docai.devtools.samples import HAND, SANS, Line, Page, render_page  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "handwritten"
TOKEN = re.compile(r"\{\{(.*?)\|(.*?)\}\}")
AR_LETTER = re.compile(r"[ء-ي]")
LAT_SIZE, AR_SIZE = 46, 52
INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫", "0123456789,.")  # Latin handwriting font has no Arabic-Indic digits


def ar_width(text, size):
    f = ImageFont.truetype(str(SANS), size + 6, layout_engine=ImageFont.Layout.RAQM)
    return f.getlength(text, direction="rtl", language="ar")


def place(text, rule, x0, x1, size_lat=LAT_SIZE, size_ar=AR_SIZE) -> Line:
    """One handwritten line with its baseline on `rule`; Arabic lines are right-aligned."""
    if AR_LETTER.search(text):
        size = size_ar
        while ar_width(text, size) > x1 - x0 - 20:
            size -= 2
        return Line(int(x1 - 10 - ar_width(text, size) - 20), rule - 8 - 74 - (size - AR_SIZE), text, "handwritten", "ar", size, tilt=0.3)
    text = text.translate(INDIC)
    f = ImageFont.truetype(str(HAND), LAT_SIZE + 4, layout_engine=ImageFont.Layout.RAQM)
    size = size_lat
    while f.getlength(text) > x1 - x0 - 20 and size > 30:
        size -= 2
        f = ImageFont.truetype(str(HAND), size + 4, layout_engine=ImageFont.Layout.RAQM)
    return Line(x0 + 10 - 20, rule - 46, text, "handwritten", "en", size, tilt=0.3)


def preview(t, lay):
    paper = Image.open(OUT / "sheets" / f"{t['id']}_{t['design']}.png").convert("RGB")
    rules, x0, x1 = lay["rules"], lay["x0"], lay["x1"]
    rows = wrap_lines(TOKEN.sub(r"\1", t["body"]), cpl_for(lay, t["lang"]))
    lines, strike = [], None
    m = TOKEN.search(t["body"])
    for i, txt in enumerate(rows):
        if not txt.strip():
            continue
        lines.append(place(txt, rules[i], x0, x1))
        if m and m[1] in txt and strike is None:
            f = ImageFont.truetype(str(HAND), LAT_SIZE + 4, layout_engine=ImageFont.Layout.RAQM)
            pre = f.getlength(txt[: txt.index(m[1])])
            sx = x0 + 10 + pre
            strike = (sx, sx + f.getlength(m[1]), rules[i])
            lines.append(Line(int(sx - 10), rules[i] - 46 - 44, m[2], "handwritten", "en", 36, tilt=0.5))
    for key, val in (t.get("fields") or {}).items():
        fx0, fx1, base = lay["fields"][key]
        lines.append(place(val, base, fx0, fx1, 40, 44))
    if t.get("margin_note"):
        mn = t["margin_note"]
        mx0, mx1 = lay["margin"]
        for j, txt in enumerate(mn["lines"]):
            lines.append(Line(mx0 - 10, rules[mn["at_line"] - 1 + j] - 44, txt, "handwritten", "en", 34, tilt=0.5))
    canvas, _ = render_page(Page(lines=lines, doc=t["id"]), seed=t["n"])
    if strike:
        d = ImageDraw.Draw(canvas)
        sx0, sx1, y = strike
        pts = [(sx0 - 6 + k * (sx1 - sx0 + 12) / 12, y - 24 + (6 if k % 2 else -4)) for k in range(13)]
        d.line(pts, fill=40, width=5)
    ink = ImageOps.colorize(canvas, black=(15, 25, 95), white=(255, 255, 255))
    out = ImageChops.multiply(paper, ink)
    return out.resize((out.width // 2, out.height // 2), Image.LANCZOS)


def main():
    layout = json.loads((OUT / "paper" / "layout.json").read_text())
    d = OUT / "preview_filled"
    d.mkdir(exist_ok=True)
    for t in TEXTS:
        preview(t, layout[t["id"]]).save(d / f"PREVIEW_{t['id']}_{t['design']}.png", optimize=True, dpi=(150, 150))
    print(len(TEXTS), "previews")


if __name__ == "__main__":
    main()
