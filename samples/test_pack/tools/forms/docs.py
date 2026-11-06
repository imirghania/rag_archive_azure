"""Writes WHAT_TO_WRITE.md/.pdf, answer_key.md, questions.md and README.md from the form declarations."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from lib import Cross, Sig, Tick, has_ar, put, width

DOSSIERS = {
    "FIN-C92-S1-F0001": ("Purchasing cycle", ["F03", "F04", "F12", "F13"]),
    "FIN-C93-S1-F0001": ("Cash and expenses", ["F02", "F05", "F06"]),
    "FIN-C94-S1-F0001": ("Meeting and fleet", ["F08", "F11"]),
    "HR-C92-S1-F0001": ("English HR forms", ["F01", "F07", "F09"]),
    "HR-C93-S1-F0001": ("Arabic and bilingual HR forms", ["F15", "F14", "F10"]),
}
LANG = {"en": "English", "ar": "Arabic", "bi": "English + Arabic"}


def shown_lang(text: str) -> str:
    if has_ar(text):
        return "Arabic + English" if re.search(r"[A-Za-z]{2}", text) else ("Arabic-Indic digits" if re.fullmatch(r"[٠-٩/.\s]+", text) else "Arabic")
    return "Digits" if not re.search(r"[A-Za-z]{2}", text) else "English"


def parts(z) -> list[tuple[str, str]]:
    """(kind, text): 'say' is an instruction, 'text' is what to write, exactly."""
    s = z.write
    if s is None:
        return [("say", "Leave empty")]
    if isinstance(s, Tick):
        return [("say", "Tick the box:"), ("text", z.options[s.i])]
    if isinstance(s, Sig):
        return [("say", "Sign with your normal signature")]
    if isinstance(s, Cross):
        return [("say", "Write:"), ("text", s.old), ("say", "cross it out with one line, then write beside it:"), ("text", s.new)]
    if isinstance(s, list):
        out: list[tuple[str, str]] = []
        for i, t in enumerate(s, 1):
            out += [("say", f"Line {i}:"), ("text", t)] if len(s) > 1 else [("text", t)]
        return out
    return [("text", s)]


def lang_of(z) -> str:
    s = z.write
    if isinstance(s, Tick):
        return "Tick"
    if isinstance(s, Sig):
        return "Signature"
    if s is None:
        return "-"
    if isinstance(s, Cross):
        return shown_lang(s.new)
    return shown_lang(" ".join(s) if isinstance(s, list) else s)


def note_of(z) -> str:
    n = z.note
    if isinstance(z.write, Cross):
        n = ("CORRECTION. " + n).strip()
    if isinstance(z.write, Tick):
        n = (n + " Tick only this box.").strip()
    if isinstance(z.write, Sig) and not n:
        n = "Sign with your normal signature."
    return n


def md_cell(ps: list[tuple[str, str]]) -> str:
    return "<br>".join(f"`{t}`" if k == "text" else t for k, t in ps)


# ------------------------------------------------------------------ shared text
def global_blocks(forms) -> list[tuple]:
    b: list[tuple] = [
        ("h1", "What to write on the test forms"),
        ("p", "Print the forms, write on them by hand exactly as listed below, scan them, group the scans into dossiers and upload. "
              "Keep this document next to you. All names, numbers and data are made up."),
        ("h2", "1. Printing"),
        ("b", "Print each form F01 to F15 on A4 paper, one side, one page each."),
        ("b", "In the print dialog choose ACTUAL SIZE (100%). NEVER choose Fit to page: the zones are sized for real size."),
        ("b", "Black and white is fine. Do not print the PREVIEW_ images, answer_key.md, questions.md or this document into the scan batch."),
        ("h2", "2. Pen and writing"),
        ("b", "Use a black or dark blue ballpoint or gel pen. No pencil, no highlighter, no thick felt tip."),
        ("b", "Write naturally, at your normal speed and with your normal handwriting. Do not print neat capitals unless the table says so."),
        ("b", "Copy the text exactly: same digits, commas, dots, slashes, spaces and capital letters. Write inside the boxes, never over printed text or the grey Z labels."),
        ("b", "Arabic is written from right to left, as you normally write it. Arabic-Indic digits (for example 12/03/2026 written with Arabic digits) are given where needed."),
        ("b", "CORRECTION rows: write the first value, cross it out with ONE straight line (it must stay readable), then write the second value beside it. The second value is the true one."),
        ("b", "Margin note rows: write small, as a quick note. Signature rows: sign with your normal signature, no printed name. Checkbox rows: tick the one box named, with a normal tick."),
        ("b", "Rows marked Leave empty stay empty on purpose. If you make a mistake that is not a planned correction, start the page again."),
        ("h2", "3. Scanning"),
        ("b", "Flatbed scanner: 300 dpi, grayscale or colour. Phone: use a scanner app, flat cropped result, even light, all four corners visible."),
        ("b", "One page per scan, or one multi-page TIFF or PDF. Keep the pages straight."),
        ("h2", "4. Naming and grouping into dossiers"),
        ("p", "A dossier ID looks like FIN-C92-S1-F0001: department (FIN or HR), -C and two digits, -S and one digit, -F and four digits. "
              "Make one folder per dossier, named with the ID, and put its scans in the order given here. "
              "Page order matters; each page starts its own document (the system cuts on the capital-letter title and the Ref line)."),
    ]
    for did, (label, codes) in DOSSIERS.items():
        names = ", ".join(f"{c} {next(f.title.title() for f in forms if f.code == c)}" for c in codes)
        b.append(("b", f"{did}  ({label}): {names}."))
    b += [
        ("p", "Example: folder FIN-C92-S1-F0001 holds scan_001.pdf (4 pages: F03, F04, F12, F13, in that order) or four single-page scans named 001, 002, 003, 004."),
        ("h2", "5. Upload"),
        ("b", "Open the web app and sign in as Sara. Click Upload. Choose the Department (FIN or HR) of the dossier and keep Mode on By dossier."),
        ("b", "Type the dossier ID, choose the scan file or files, click Check files, then Confirm and upload."),
        ("b", "The local dev server cannot read real handwriting (its readers are fixtures). Real reading needs the Azure deployment."),
        ("b", "Never upload this document, answer_key.md, questions.md or the PREVIEW_ images."),
    ]
    return b


def form_blocks(forms) -> list[tuple]:
    b: list[tuple] = []
    for f in forms:
        b.append(("h2", f"{f.code}  {f.title.title()}   ({LANG[f.lang]}, {f.dept})"))
        b.append(("p", f"File: {f.file} (and {f.code}_{f.slug}.png). Dossier: {f.dossier}. Printed Ref: {f.ref}. Purpose: {f.purpose}"))
        rows = [[[("say", z.id)], [("say", z.where)], parts(z), [("say", lang_of(z))], [("say", note_of(z))]] for z in f.zones]
        b.append(("table", ["Zone", "Where on the page", "Write exactly", "Language", "Note"], rows))
    return b


# ------------------------------------------------------------------ markdown
def to_md(blocks: list[tuple]) -> str:
    out: list[str] = []
    for blk in blocks:
        k = blk[0]
        if k == "h1":
            out.append(f"# {blk[1]}\n")
        elif k == "h2":
            out.append(f"\n## {blk[1]}\n")
        elif k == "p":
            out.append(blk[1] + "\n")
        elif k == "b":
            out.append(f"- {blk[1]}")
        else:
            out.append("")
            out.append("| " + " | ".join(blk[1]) + " |")
            out.append("| " + " | ".join("---" for _ in blk[1]) + " |")
            for r in blk[2]:
                out.append("| " + " | ".join(md_cell(c) for c in r) + " |")
            out.append("")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ pdf (A4 landscape, 200 dpi, big type)
PW, PH, M, FS, LH = 2339, 1654, 70, 33, 46
COLS = [130, 590, 750, 250, 479]


def wrap(text: str, size: int, maxw: int, bold: bool = False) -> list[str]:
    rows, cur = [], ""
    for w in text.split():
        if cur and width(f"{cur} {w}", size, bold) > maxw:
            rows.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    return rows + [cur]


class Pdf:
    def __init__(self) -> None:
        self.pages: list[Image.Image] = []
        self.new()

    def new(self) -> None:
        from PIL import ImageDraw
        self.img = Image.new("L", (PW, PH), 255)
        self.d = ImageDraw.Draw(self.img)
        self.pages.append(self.img)
        self.y = M + 40

    def text(self, t: str, size: int = FS, bold: bool = False, x: int = M, maxw: int = PW - 2 * M, gap: int = 14) -> None:
        for r in wrap(t, size, maxw, bold):
            if self.y + LH > PH - M:
                self.new()
            if has_ar(r):
                put(self.d, x + maxw, self.y, r, size, bold, "r")
            else:
                put(self.d, x, self.y, r, size, bold, "l")
            self.y += int(size * 1.4)
        self.y += gap

    def cell_height(self, ps: list[tuple[str, str]], w: int) -> int:
        return sum(len(wrap(t, FS, w - 24, k == "text")) * LH for k, t in ps) + 20

    def row(self, cells: list[list[tuple[str, str]]], head: bool = False) -> None:
        h = max(self.cell_height(c, w) for c, w in zip(cells, COLS))
        if self.y + h > PH - M:
            self.new()
            if not head:
                self.row_header()
        x = M
        top = self.y
        if head:
            self.d.rectangle((M, top, M + sum(COLS), top + h), fill=225)
        for c, w in zip(cells, COLS):
            self.d.rectangle((x, top, x + w, top + h), outline=120, width=2)
            yy = top + 10 + FS
            for k, t in c:
                for r in wrap(t, FS, w - 24, k == "text"):
                    bold = k == "text" or head
                    if has_ar(r):
                        put(self.d, x + w - 12, yy, r, FS, bold, "r")
                    else:
                        put(self.d, x + 12, yy, r, FS, bold, "l")
                    yy += LH
            x += w
        self.y += h

    def row_header(self) -> None:
        self.row([[("say", t)] for t in self.head], head=True)


def to_pdf(blocks: list[tuple], path: Path) -> None:
    p = Pdf()
    for blk in blocks:
        k = blk[0]
        if k == "h1":
            p.text(blk[1], 56, True, gap=24)
        elif k == "h2":
            if re.match(r"F\d\d ", blk[1]):
                p.new()
            elif p.y > PH - 300:
                p.new()
            p.y += 20
            p.text(blk[1], 44, True, gap=10)
        elif k == "p":
            p.text(blk[1], FS)
        elif k == "b":
            p.text("-  " + blk[1], FS, gap=8)
        else:
            p.head = blk[1]
            p.row_header()
            for r in blk[2]:
                p.row(r)
            p.y += 20
    # shortcut: JPEG pages (Pillow's PDF writer has no lossless grey option), quality 60 is still sharp at 200 dpi
    p.pages[0].save(path, "PDF", resolution=200.0, quality=60, save_all=True, append_images=p.pages[1:])


# ------------------------------------------------------------------ answer key and questions
def expected(z) -> str:
    s = z.write
    if s is None:
        return "(empty)"
    if isinstance(s, Tick):
        return f"ticked: {z.options[s.i]}"
    if isinstance(s, Sig):
        return "(a signature, no readable text expected)"
    if isinstance(s, Cross):
        return f"`{s.new}`   (the first value `{s.old}` was crossed out; `{s.new}` is the true value)"
    return " / ".join(f"`{t}`" for t in (s if isinstance(s, list) else [s]))


def answer_key(forms) -> str:
    out = ["# Answer key", "",
           "What should have been written in each zone, so you can compare it with what the system read. "
           "For a crossed-out correction the system should use the corrected (second) value. Do not upload this file.", ""]
    for f in forms:
        out += [f"## {f.code} {f.title.title()} ({f.file}), dossier {f.dossier}", "", f"Printed: title {f.title}, Ref: {f.ref}", "",
                "| Zone | What the zone should contain | Written language | Remark |", "| --- | --- | --- | --- |"]
        out += [f"| {z.id} | {expected(z)} | {lang_of(z)} | {note_of(z)} |" for z in f.zones]
        out.append("")
    return "\n".join(out)


Q = {
    "FIN-C92-S1-F0001": [
        ("What is the grand total of purchase order PO-2026-0417?", "EN", "1,230.60 EGP", "numeric"),
        ("What unit price was written for the Toner cartridge HP-85 on the purchase order?", "EN", "64.20 (62.40 was crossed out)", "correction"),
        ("How many toner cartridges were ordered and how many were received?", "EN", "Ordered 6, received 4 (5 was crossed out)", "numeric, correction"),
        ("ما المبلغ الذي تمت الموافقة عليه في ورقة اعتماد الفاتورة INV-55120؟", "AR over EN form", "1,102.20 (مبلغ الفاتورة)", "numeric"),
        ("To whom was the cheque requested and for what amount?", "EN over AR form", "Sunrise Office Supplies (صن رايز لمستلزمات المكاتب), 1102.20 (١١٠٢.٢٠); 1230.60 was crossed out", "correction"),
        ("What is the supplier's bank account number?", "EN", "Not in the documents", "not in documents"),
    ],
    "FIN-C93-S1-F0001": [
        ("What is the total claimed on Layla Mansour's expense claim?", "EN", "1,963.25 EGP", "numeric"),
        ("How much did the two-night hotel stay cost?", "EN", "1,420.00 (1,240.00 was crossed out)", "numeric, correction"),
        ("كم بلغ إجمالي الإيداع المصرفي بتاريخ 12.03.2026؟", "AR over EN form", "8,900.50 (8,090.50 was crossed out)", "numeric, correction"),
        ("Who was paid by petty cash voucher FIN/PC/2026/0319 and for what?", "EN over bilingual form", "محمود عادل (Mahmoud Adel), 86.50 EGP, shipping fee via FastRoute no. 7741", "mixed Arabic/English"),
        ("What is the account number of the deposit slip?", "EN", "4471 0093 2258", "digits"),
        ("What is the name of the person who approved the petty cash voucher?", "EN", "Not in the documents (only a signature, no printed or written name)", "not in documents"),
    ],
    "FIN-C94-S1-F0001": [
        ("What budget ceiling was set for Q1 at the meeting on 11 March 2026?", "EN", "480,000", "numeric"),
        ("من المسؤول عن إعداد سياسة السفر المعدلة وما موعد التسليم؟", "AR over EN form", "Omar Farouk, 20/03/2026", "date"),
        ("What did the margin notes of the meeting say?", "EN", "'check with Hana' and 're: travel 12%?'", "margin note"),
        ("What was the total maintenance cost of vehicle FLT-07, and when is the next service due?", "EN", "1,750.00 EGP; at 90,000 km (June 2026)", "numeric"),
        ("Which garage will carry out the next service?", "EN", "Not in the documents", "not in documents"),
    ],
    "HR-C92-S1-F0001": [
        ("How many working days of leave did Layla Mansour request, and from when to when?", "EN", "7 working days, 12/03/2026 to 20 March 2026", "numeric, dates"),
        ("Was the leave approved, and what did the manager remark?", "EN", "Approved. 'Approved. Omar to cover the approvals queue.'", "checkbox, margin note"),
        ("How many hours did she work in the week ending 13/03/2026?", "EN", "36.5 hours", "numeric"),
        ("What is Layla Mansour's mobile number?", "EN", "+20 100 555 0143 (+20 100 555 0134 was crossed out)", "correction, digits"),
        ("ما اسم جهة الاتصال في حالات الطوارئ وما صلتها بالموظفة؟", "AR over bilingual form", "Samir Mansour, brother (أخ)", "EN content"),
        ("What is Layla Mansour's salary grade?", "EN", "Not in the documents", "not in documents"),
    ],
    "HR-C93-S1-F0001": [
        ("كم يوماً طلب سامي عبد الله إجازة ولماذا؟", "AR", "٥ أيام، وعكة صحية (تقرير طبي من مستشفى الأمل)", "numeric"),
        ("ما قرار المدير العام في المذكرة الرسمية وما تاريخ التنفيذ؟", "AR", "تمت الموافقة على التعميم، يُنفَّذ اعتباراً من ٠١/٠٦/٢٠٢٦", "handwritten Arabic, date"),
        ("What working hours does the memo announce for the summer?", "EN over AR form", "8:00 am to 2:00 pm, Sunday to Thursday (printed text)", "printed Arabic"),
        ("How many visitors are in the visitor log of 12 Mar 2026, and who came to see Hana Saleh?", "EN over bilingual form", "3 visitors; Nadia Fawzy of Delta Print", "numeric"),
        ("What is the visitor's car registration number?", "EN", "Not in the documents", "not in documents"),
    ],
}


def questions(forms) -> str:
    out = ["# Test questions", "",
           "Ask these in the web app after the dossiers are processed. Types: numeric, correction (the system must use the corrected value, "
           "not the crossed-out one), not in documents (the right answer is that the documents do not say). Do not upload this file.", ""]
    for did, qs in Q.items():
        label, codes = DOSSIERS[did]
        out += [f"## {did} ({label}: {', '.join(codes)})", "", "| # | Question | Language | Expected answer | Type |", "| --- | --- | --- | --- | --- |"]
        out += [f"| {i} | {q} | {lang} | {a} | {t} |" for i, (q, lang, a, t) in enumerate(qs, 1)]
        out.append("")
    return "\n".join(out)


def readme(forms) -> str:
    rows = "\n".join(f"| `{f.file}`, `{f.code}_{f.slug}.png` | {f.title.title()} | {LANG[f.lang]} | {f.dept} | {f.dossier} | {len(f.zones)} | Print, fill, scan, upload |" for f in forms)
    return f"""# Handwriting test forms (15 blank forms)

Printed forms to fill in BY HAND, then scan and upload as dossiers. All data is made up.

## Files

| File | Form | Language | Dept | Dossier | Zones | Use |
| --- | --- | --- | --- | --- | --- | --- |
{rows}
| `WHAT_TO_WRITE.pdf` / `.md` | Exactly what to write in every zone, plus printing, pen, scanning, grouping and upload steps | | | | | Print next to the form. NOT uploaded |
| `answer_key.md` | What each zone should contain, to compare with what the system read | | | | | NOT uploaded |
| `questions.md` | 5 to 6 test questions per dossier with expected answers | | | | | NOT uploaded |
| `zones.json` | Zone positions at 300 dpi, same schema as `samples/templates/zones.json` plus `form` and `kind` | | | | | NOT uploaded |
| `preview_filled/PREVIEW_*.png` | Simulated handwriting, only to show what a filled form looks like | | | | | NEVER upload |

## What to print

Print the 15 forms (`F01` to `F15`, PDF or PNG) on A4, actual size (never Fit to page). Optionally print `WHAT_TO_WRITE.pdf` to keep beside you.

## What NOT to upload

`WHAT_TO_WRITE.*`, `answer_key.md`, `questions.md`, `zones.json`, anything in `preview_filled/`. Upload only your scans of the filled forms, grouped by dossier as described in `WHAT_TO_WRITE`.

Notes: every page has its own capital-letter title and `Ref:` line. The Arabic-only forms (F13, F14, F15) also carry the English capital title and Ref line, because the splitter looks for them. The local runtime cannot read real handwriting; use Azure.

## Regenerate

```bash
uv run python samples/test_pack/tools/forms/make_forms.py
```

Deterministic (the PDF bytes differ only by timestamps). Sources: `samples/test_pack/tools/forms/` (`lib.py` drawing, `forms.py` layouts and texts, `docs.py` documents, `make_forms.py`).
"""


def write_docs(forms, out: Path) -> None:
    blocks = global_blocks(forms) + form_blocks(forms)
    (out / "WHAT_TO_WRITE.md").write_text(to_md(blocks))
    to_pdf(blocks, out / "WHAT_TO_WRITE.pdf")
    (out / "answer_key.md").write_text(answer_key(forms))
    (out / "questions.md").write_text(questions(forms))
    (out / "README.md").write_text(readme(forms))
    for did, (_, codes) in DOSSIERS.items():
        assert {f.dossier for f in forms if f.code in codes} == {did}, did
