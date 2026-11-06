"""Printable test templates: blank forms to print, write on by hand, scan and upload as a dossier.

Every page is A4 at 300 dpi, grayscale, saved as PDF. The writing zones (Z1, Z2, ...) are listed in zones.json.
Also writes `filled/<dossier>/`: the same pages with simulated handwriting plus a manifest, and (with --fixtures)
the OCR and second-reader fixtures the LOCAL runtime needs to process that dossier. The local runtime cannot
read real handwriting; the fixtures stand in for Document Intelligence and the vision model.

    uv run python -m docai.devtools.templates --out samples/templates [--fixtures samples/out/fixtures]

Needs Pillow only. The layout facts that the pipeline relies on:
- the printed text of the memo ends at x=1480 and the margin zone starts at x=1640, so a note written there is
  wholly right of the printed column and is attached to the paragraph beside it;
- every page has its own capital-letter title and its own `Ref:` line, so each page starts a new document;
- no page prints text to the right of where its handwriting starts, except the memo margin on purpose.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw

from .samples import (
    FONT_DIR,
    HAND,
    INK,
    SANS,
    SERIF,
    H,
    Line,
    Page,
    W,
    _fixture_ocr,
    _fixture_vlm,
    _font,
    _save_tiff,
    _sha,
    render_page,
)

DOSSIER = "FIN-C99-S1-F0001"
SEED = 7
PITCH = 110  # ruled line spacing in px: 9.3 mm, room for ordinary handwriting
MEMO_TEXT_RIGHT = 1480  # the memo's printed column ends here
MARGIN_X0 = 1640  # the memo margin zone starts here: 740 px, 6.3 cm wide
GRAY_RULE, GRAY_BOX, GRAY_LABEL = 160, 120, 150  # light enough that a zone counts as blank
SANS_B = FONT_DIR / "dejavu/DejaVuSans-Bold.ttf"


@dataclass
class Zone:
    id: str
    template: str
    page: int
    x0: int
    y0: int
    x1: int
    y1: int
    language: str  # en | ar | en+ar | digits
    purpose: str
    ruled_lines: list[int] = field(default_factory=list)  # y of each baseline
    tmpl: str = ""  # short name used in the answer key (t1 .. t4)


@dataclass
class Hand:
    """Simulated handwriting for the filled example, placed in a zone."""
    zone: str
    text: str
    lang: str = "en"
    size: int = 36
    line: int = 0  # which ruled line of the zone
    align: str = "left"
    ocr_text: str | None = None
    ocr_conf: float | None = None
    vlm_text: str | None = None
    tier: str = "handwritten_dual_agreed"
    note: str = ""


@dataclass
class Template:
    file: str
    base: Image.Image  # rules, boxes and zone labels (not read by OCR)
    lines: list[Line]  # printed text (read by OCR)
    zones: list[Zone]
    hands: list[Hand]


class _Ids:
    def __init__(self) -> None:
        self.n = 0

    def next(self) -> str:
        self.n += 1
        return f"Z{self.n}"


def _label(d: ImageDraw.ImageDraw, zid: str, x: int, y: int) -> None:
    d.text((x, y), zid, font=_font(SANS, 22), fill=GRAY_LABEL)


def _ruled(t: Template, ids: _Ids, tmpl: str, x0: int, x1: int, first: int, n: int, lang: str, purpose: str,
        label_left: bool = False) -> Zone:
    """A zone of n ruled lines; `first` is the y of the first baseline. The label sits left of the zone or in its corner."""
    d = ImageDraw.Draw(t.base)
    ys = [first + PITCH * i for i in range(n)]
    for y in ys:
        d.line((x0, y, x1, y), fill=GRAY_RULE, width=2)
    z = Zone(ids.next(), t.file, 1, x0, first - 100, x1, ys[-1] + 10, lang, purpose, ys, tmpl)
    _label(d, z.id, x0 - 62 if label_left else x0 + 6, first - 96 if not label_left else first - 30)
    t.zones.append(z)
    return z


def _cell(t: Template, ids: _Ids, tmpl: str, x0: int, y0: int, x1: int, y1: int, lang: str, purpose: str) -> Zone:
    d = ImageDraw.Draw(t.base)
    d.rectangle((x0, y0, x1, y1), outline=GRAY_BOX, width=3)
    z = Zone(ids.next(), t.file, 1, x0, y0, x1, y1, lang, purpose, [y0 + int(0.68 * (y1 - y0))], tmpl)
    _label(d, z.id, x0 + 8, y0 + 6)
    t.zones.append(z)
    return z


def _p(x: int, y: int, text: str, size: int = 42, bold: bool = False) -> Line:
    return Line(x, y, text, size=size, bold=bold, tier="printed_high_conf")


def _para(x: int, y: int, text: str, maxw: int, size: int = 42) -> tuple[list[Line], int]:
    """Wraps a paragraph to maxw px; returns its lines and the y after a blank line."""
    f = _font(SERIF, size)
    rows: list[str] = []
    cur = ""
    for word in text.split():
        if cur and f.getlength(f"{cur} {word}") > maxw:
            rows.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    rows.append(cur)
    return [_p(x, y + 58 * i, r, size) for i, r in enumerate(rows)], y + 58 * (len(rows) + 1)


def _header(t: Template, title: str, ref: str, date: str, y: int = 250) -> int:
    t.lines += [_p(200, y, title, 56, True), _p(200, y + 100, f"Ref: {ref}"), _p(200, y + 158, f"Date: {date}")]
    return y + 158


# ------------------------------------------------------------------------------------------------
# The four templates
# ------------------------------------------------------------------------------------------------
def _t1(ids: _Ids) -> Template:
    t = Template("t1_memo_with_margin_note.pdf", Image.new("L", (W, H), 255), [], [], [])
    y = _header(t, "INTERNAL MEMORANDUM", "FIN/TPL/001", "14 March 2008")
    t.lines += [_p(200, y + 58, "To: Finance Director"), _p(200, y + 116, "From: Head of Procurement"),
                _p(200, y + 174, "Subject: Renewal of warehouse lease, Plot 118")]
    d = ImageDraw.Draw(t.base)
    d.line((200, y + 270, 2280, y + 270), fill=GRAY_BOX, width=3)
    y += 340
    paras = [("The landlord has offered to renew the warehouse lease on Plot 118 for a further three years. The annual "
            "rent is unchanged from the current term."),
            ("Procurement recommends that we accept the offer. The first quarterly payment falls due on 1 April 2008, "
            "so a decision is needed this month."),
            ("Please approve the renewal and the first payment. Write your approval, your initials and the date in "
            "the right margin beside this paragraph, then sign below.")]
    for i, text in enumerate(paras):
        lines, nxt = _para(200, y, text, MEMO_TEXT_RIGHT - 200)
        t.lines += lines
        if i == 2:
            top = y
        y = nxt
    first = top + 70  # first margin line sits beside the second row of paragraph 3
    for tag, lang, purpose in (("note", "en", "Margin note: approval, amount"), ("initials", "en", "Margin: initials"),
                            ("date", "digits", "Margin: date, as numbers")):
        _ruled(t, ids, "t1", MARGIN_X0, 2380, first, 1, lang, purpose, label_left=True)
        first += PITCH
    t.lines.append(_p(200, 2620, "Signature or initials:", 36))
    _cell(t, ids, "t1", 200, 2690, 1100, 2870, "en", "Signature or initials box")
    z = [z.id for z in t.zones]
    t.hands = [Hand(z[0], "Approved, pay 1,750 by 15/3", ocr_conf=0.84), Hand(z[1], "K.A.M.", ocr_conf=0.8),
            Hand(z[2], "15/3/2008", ocr_conf=0.86), Hand(z[3], "K. Al Mansoori", size=40, ocr_conf=0.82)]
    return t


def _t2(ids: _Ids) -> Template:
    t = Template("t2_invoice_amounts.pdf", Image.new("L", (W, H), 255), [], [], [])
    y = _header(t, "TAX INVOICE", "FIN/TPL/002", "3 March 2008")
    t.lines += [_p(200, y + 58, "Customer: Gulf Trading Company"),
                _p(200, y + 150, "Write the quantity, unit price and total in each empty box. Use digits only.", 34)]
    cols = [200, 1180, 1580, 1960, 2280]
    top, head_h, row_h = 800, 90, 150
    d = ImageDraw.Draw(t.base)
    for name, x in zip(("Item", "Quantity", "Unit price", "Total (AED)"), cols):
        t.lines.append(_p(x + 20, top + 22, name, 34, True))
    items = ["Storage, pallet position", "Handling, per pallet", "Forklift hire, per hour", "Packing material", "Delivery, per trip"]
    for i, item in enumerate(items):
        t.lines.append(_p(220, top + head_h + i * row_h + 52, item, 36))
    # the table frame; the three digit columns are drawn as boxes by _cell below
    d.rectangle((cols[0], top, cols[-1], top + head_h), outline=GRAY_BOX, width=3)
    for i in range(len(items) + 1):
        yy = top + head_h + i * row_h
        d.line((cols[0], yy, cols[1], yy), fill=GRAY_BOX, width=3)
    d.line((cols[0], top + head_h, cols[0], top + head_h + len(items) * row_h), fill=GRAY_BOX, width=3)
    for x in cols[1:4]:
        d.line((x, top, x, top + head_h), fill=GRAY_BOX, width=3)
    values = [("7", "1,750", "12,250"), ("15", "125", "1,875"), ("60", "650", "39,000"), ("5", "2,070", "10,350"), ("10", "900", "9,000")]
    names = ("quantity", "unit price", "total")
    z_of: dict[tuple[int, int], str] = {}
    for r in range(len(items)):
        for c in range(3):
            z = _cell(t, ids, "t2", cols[c + 1], top + head_h + r * row_h, cols[c + 2], top + head_h + (r + 1) * row_h,
                    "digits", f"Row {r + 1} {names[c]}")
            z_of[r, c] = z.id
    gy = top + head_h + len(items) * row_h + 40
    t.lines.append(_p(1050, gy + 52, "Grand total (AED)", 38, True))
    grand = _cell(t, ids, "t2", cols[3], gy, cols[4], gy + row_h, "digits", "Grand total")
    t.lines.append(_p(200, 2080, "Paid on:", 38, True))
    paid = _cell(t, ids, "t2", 200, 2150, 1000, 2300, "digits", "Paid on (date)")
    t.lines.append(_p(1300, 2080, "Approved by:", 38, True))
    appr = _cell(t, ids, "t2", 1300, 2150, 2280, 2300, "en", "Approved by (name)")
    t.hands = [Hand(z_of[r, c], values[r][c], size=44, ocr_conf=0.9) for r in range(5) for c in range(3)]
    # one digit that the first reader gets wrong (7 read as 1) and one 0 read as 6: the readers disagree, a task appears
    t.hands[1] = Hand(z_of[0, 1], "1,750", size=44, ocr_text="1,150", ocr_conf=0.78, vlm_text="1,750", tier="unverified",
                    note="digits disagree (7 read as 1)")
    t.hands[8] = Hand(z_of[2, 2], "39,000", size=44, ocr_text="39,006", ocr_conf=0.88, vlm_text="39,000", tier="unverified",
                    note="digits disagree (0 read as 6)")
    t.hands += [Hand(grand.id, "72,475", size=44, ocr_conf=0.9), Hand(paid.id, "3/4/2008", size=42, ocr_conf=0.85),
                Hand(appr.id, "K. Al Mansoori", size=42, ocr_conf=0.82)]
    return t


def _t3(ids: _Ids) -> Template:
    t = Template("t3_english_and_arabic_notes.pdf", Image.new("L", (W, H), 255), [], [], [])
    y = _header(t, "COMPLAINT FOLLOW-UP", "FIN/TPL/003", "9 June 2008")
    t.lines.append(_p(200, y + 58, "Subject: Delayed vendor payment"))
    # long lines on purpose: printed text reaches x=2100, so right-aligned Arabic is not mistaken for a margin note
    body, _ = _para(200, y + 190, "The vendor reports that invoice INV-3301 was paid twenty days late and asks for a written reply. "
                    "Please record your follow-up below: one note in English, one in Arabic, and one line that mixes both. "
                    "Write inside the ruled areas.", 2050)
    t.lines += body
    t.lines.append(_p(200, 1000, "English note", 38, True))
    en = _ruled(t, ids, "t3", 260, 2280, 1180, 3, "en", "English note")
    t.lines.append(_p(200, 1560, "Arabic note (write from right to left)", 38, True))
    ar = _ruled(t, ids, "t3", 260, 2280, 1740, 3, "ar", "Arabic note, right to left")
    t.lines.append(_p(200, 2120, "Mixed English and Arabic line", 38, True))
    mx = _ruled(t, ids, "t3", 260, 2280, 2300, 2, "en+ar", "Mixed English and Arabic line")
    t.hands = [
        Hand(en.id, "Vendor will be paid on 5/4 after review.", ocr_conf=0.83),
        Hand(en.id, "Reply sent 6/4.", line=1, ocr_conf=0.8),
        Hand(ar.id, "تمت الموافقة", lang="ar", align="right", ocr_conf=0.81),
        # OCR cannot read this one confidently: it cannot vote and the line becomes a review task
        Hand(ar.id, "يُرجى المتابعة", lang="ar", line=1, align="right", ocr_text="يرجى المتابعة", ocr_conf=0.52,
            vlm_text="يُرجى المتابعة", tier="unverified", note="ocr too unsure to vote"),
        # the simulator cannot mix scripts in one line, so the mixed zone gets an English and an Arabic line
        Hand(mx.id, "Paid 12,500 on 3/4/2008", ocr_conf=0.85),
        Hand(mx.id, "تمت الموافقة", lang="ar", align="right", ocr_conf=0.79),
    ]
    return t


def _t4(ids: _Ids) -> Template:
    t = Template("t4_free_handwriting.pdf", Image.new("L", (W, H), 255), [], [], [])
    t.lines += [_p(200, 160, "HANDWRITTEN LETTER", 56, True), _p(200, 260, "Ref: FIN/TPL/004"), _p(200, 340, "Date:")]
    _ruled(t, ids, "t4", 420, 1100, 400, 1, "digits", "Date of the letter", label_left=True)
    d = ImageDraw.Draw(t.base)
    _ruled(t, ids, "t4", 340, 2300, 590, 26, "en", "Free letter: 26 ruled lines")
    for y in t.zones[-1].ruled_lines:
        d.line((200, y, 340, y), fill=GRAY_RULE, width=2)  # rules continue left of the margin rule
    d.line((330, 470, 330, 3360), fill=GRAY_BOX, width=3)  # the left margin rule
    return t


TEMPLATES = (_t1, _t2, _t3, _t4)


# Rendering
def _baseline_to_y(h: Hand, baseline: int) -> int:
    """The Line.y that puts the simulated ink baseline on `baseline` (see _draw_line in samples.py)."""
    if h.lang == "ar":
        return baseline - 20 - round(_font(SANS, h.size + 6).getmetrics()[0])
    return baseline - round(_font(HAND, h.size + 4).getmetrics()[0])


def _hand_line(z: Zone, h: Hand) -> Line:
    if h.lang == "ar":
        width = _font(SANS, h.size + 6).getlength(h.text, direction="rtl", language="ar")
    else:
        width = _font(HAND, h.size + 4).getlength(h.text)
    x = z.x0 + 24 if h.align == "left" else int(z.x1 - 24 - width)
    return Line(x, _baseline_to_y(h, z.ruled_lines[h.line] - 8), h.text, "handwritten", h.lang, h.size, ocr_text=h.ocr_text,
                ocr_conf=h.ocr_conf, vlm_text=h.vlm_text, tier=h.tier, note=h.note, tilt=0.5)


def render_blank(t: Template, seed: int) -> tuple[Image.Image, list[dict]]:
    return render_page(Page(list(t.lines), "T"), seed, base=t.base.copy())


def render_filled(t: Template, seed: int) -> tuple[Image.Image, list[dict]]:
    zones = {z.id: z for z in t.zones}
    hand = [_hand_line(zones[h.zone], h) for h in t.hands]
    return render_page(Page(list(t.lines) + hand, "T"), seed, base=t.base.copy())


def _save_pdf(frames: list[Image.Image], path: Path) -> None:
    frames[0].save(path, "PDF", resolution=300.0, quality=90, save_all=True, append_images=frames[1:])


def _wrap_draw(d: ImageDraw.ImageDraw, x: int, y: int, text: str, size: int, maxw: int, bold: bool = False) -> int:
    """Draws wrapped sans text, returns the y below it."""
    f = _font(SANS_B if bold else SANS, size)
    row = ""
    for word in text.split() + [None]:
        if word is None or (row and f.getlength(f"{row} {word}") > maxw):
            d.text((x, y), row, font=f, fill=INK)
            y += int(size * 1.4)
            row = word or ""
        else:
            row = f"{row} {word}".strip()
    return y


def _instructions() -> Image.Image:
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    x, mw = 180, W - 360
    d.rectangle((x, 110, W - x, 310), outline=INK, width=8)
    d.text((x + 40, 130), "NOT FOR UPLOAD", font=_font(SANS_B, 76), fill=INK)
    d.text((x + 40, 235), "This page is the instructions. Do not scan it. Do not upload it.", font=_font(SANS, 46), fill=INK)
    y = 360
    d.text((x, y), "How to use the templates", font=_font(SANS_B, 74), fill=INK)
    y += 130
    sections = [
        ("1. Print", ["Print t1, t2, t3 and t4. One A4 page each.",
                    "In the print dialog choose \"Actual size\" or \"100%\". Do NOT choose \"Fit to page\"."]),
        ("2. Pen", ["Black or dark blue ballpoint or gel pen.", "Not a pencil. Not a highlighter."]),
        ("3. Write", ["Write the way you normally write. That is the point.",
                    "Write inside the boxes and on the lines. Do not write on the printed text.",
                    "Small grey labels Z1, Z2 ... mark each writing zone.",
                    "English texts you can copy:", "•  Approved, pay 1,750 by 15/3", "•  Paid 12,500 on 3/4/2008",
                    "Arabic texts you can copy:",
                    "Digits for the invoice boxes: use some 7, 1, 5, 6 and 0.",
                    "Do not write real names, numbers or secrets. Use made-up data."]),
        ("4. Scan", ["300 dpi. Grayscale or black and white. TIFF or PDF.",
                    "Put the pages in order (t1, t2, t3, t4) in ONE file. Keep each page straight, all four corners in view."]),
        ("5. Upload", ["Dossier ID to type: for example FIN-C98-S1-F0001.", "Department: FIN.   Mode: By dossier.   Sign in as sara."]),
    ]
    for head, rows in sections:
        d.text((x, y), head, font=_font(SANS_B, 68), fill=INK)
        y += 100
        for r in rows:
            y = _wrap_draw(d, x + 40, y, r, 52, mw - 40)
            if r.startswith("Arabic texts"):
                f = _font(SANS, 70)
                ax = x + 80
                for phrase in ("يرجى المتابعة", "تمت الموافقة"):
                    d.text((ax, y - 12), phrase, font=f, fill=INK, direction="rtl", language="ar")
                    ax += int(f.getlength(phrase, direction="rtl", language="ar")) + 120
                y += 110
        y += 50
    d.rectangle((x, y + 20, W - x, y + 260), outline=INK, width=8)
    d.text((x + 40, y + 55), "Do not upload this page. Upload only your scans of t1 to t4.", font=_font(SANS_B, 52), fill=INK)
    d.text((x + 40, y + 150), "The answer key sheet is not for upload either.", font=_font(SANS, 46), fill=INK)
    return img


def _answer_key(zones: list[Zone]) -> list[Image.Image]:
    cols = [(200, "Zone"), (310, "Sheet"), (430, "Where"), (1000, "What I actually wrote"), (1700, "What the system read"), (2280, "")]
    row_h, per_page = 135, 20
    pages = []
    for start in range(0, len(zones), per_page):
        img = Image.new("L", (W, H), 255)
        d = ImageDraw.Draw(img)
        d.text((200, 130), "ANSWER KEY SHEET", font=_font(SANS_B, 60), fill=INK)
        _wrap_draw(d, 200, 225, "NOT FOR UPLOAD. After the system has read your pages, fill in the last two columns, zone by zone.",
                34, W - 400)
        top = 380
        f, fb = _font(SANS, 26), _font(SANS_B, 30)
        d.rectangle((200, top, 2280, top + 70), outline=GRAY_BOX, width=3)
        for x, name in cols[:-1]:
            d.text((x + 10, top + 18), name, font=fb, fill=INK)
            d.line((x, top, x, top + 70 + row_h * len(zones[start:start + per_page])), fill=GRAY_BOX, width=3)
        chunk = zones[start:start + per_page]
        for i, z in enumerate(chunk):
            y = top + 70 + i * row_h
            d.line((200, y + row_h, 2280, y + row_h), fill=GRAY_BOX, width=3)
            d.text((cols[0][0] + 10, y + 50), z.id, font=fb, fill=INK)
            d.text((cols[1][0] + 10, y + 50), z.tmpl, font=f, fill=INK)
            d.text((cols[2][0] + 10, y + 50), z.purpose, font=f, fill=INK)
        d.line((2280, top, 2280, top + 70 + row_h * len(chunk)), fill=GRAY_BOX, width=3)
        pages.append(img)
    return pages


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def generate(out: Path, fixtures: Path | None = None) -> dict:
    """Writes the templates and the filled example under `out`; fixtures (if asked for) under `fixtures/<dossier>/`."""
    out.mkdir(parents=True, exist_ok=True)
    ids = _Ids()
    templates = [build(ids) for build in TEMPLATES]
    zones = [z for t in templates for z in t.zones]
    summary: dict = {"zones": zones, "printed_right_edge": {}, "templates": templates}
    for n, t in enumerate(templates):
        img, items = render_blank(t, SEED + n)
        _save_pdf([img], out / t.file)
        printed = [it["box"]["x1"] for it in items]
        summary["printed_right_edge"][t.file] = max(printed)
    _save_pdf([_instructions()], out / "00_instructions.pdf")
    _save_pdf(_answer_key(zones), out / "answer_key_sheet.pdf")
    _write_json(out / "zones.json", {"page": {"width": W, "height": H, "dpi": 300},
                                    "zones": [{k: v for k, v in asdict(z).items() if k != "tmpl"} for z in zones]})

    # the filled example: t1, t2, t3 with simulated handwriting
    ddir = out / "filled" / DOSSIER
    ddir.mkdir(parents=True, exist_ok=True)
    fdir = fixtures / DOSSIER if fixtures else None
    if fdir:
        fdir.mkdir(parents=True, exist_ok=True)
    frames = []
    for n, t in enumerate(templates[:3], start=1):
        img, items = render_filled(t, SEED + 10 + n)
        frames.append(img)
        if fdir:
            _write_json(fdir / f"p{n:03d}.ocr.json", _fixture_ocr(n, items))
            _write_json(fdir / f"p{n:03d}.vlm.json", _fixture_vlm(items))
    tif = ddir / "scan_001.tif"
    _save_tiff(frames, tif)
    manifest = {"schema": 1, "dossier_id": DOSSIER, "source": "upload", "upload_id": None, "uploaded_by": None,
                "segmentation": "auto",
                "files": [{"name": tif.name, "bytes": tif.stat().st_size, "sha256": _sha(tif), "pages": len(frames)}]}
    _write_json(ddir / "dossier.json", manifest)
    summary["manifest"] = manifest
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=Path("samples/templates"))
    ap.add_argument("--fixtures", type=Path, default=None, help="also write the OCR and second-reader fixtures here")
    a = ap.parse_args()
    s = generate(a.out, a.fixtures)
    print(f"wrote {len(s['zones'])} zones to {a.out}" + (f" and fixtures to {a.fixtures / DOSSIER}" if a.fixtures else ""))


if __name__ == "__main__":
    main()
