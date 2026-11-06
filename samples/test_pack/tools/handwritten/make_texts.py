"""TEXTS_TO_WRITE.md/.pdf, answer_key.md, questions.md. Run make_paper.py first (needs paper/layout.json).
Run: uv run python samples/test_pack/tools/handwritten/make_texts.py"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from paperlib import FD, cpl_for, has_ar, wrap_lines
from texts_data import GROUPS, QUESTIONS, TEXTS

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from docai.contracts.keys import DOSSIER_ID_RE  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "handwritten"
TOKEN = re.compile(r"\{\{(.*?)\|(.*?)\}\}")
LANG = {"en": "English", "ar": "Arabic (right to left)", "mixed": "Arabic with English words and codes"}
DEPT = {"FIN": "Finance", "HR": "Human Resources"}
SIZE = (1240, 1754)  # A4 at 150 dpi, large type


def final(body: str) -> str:
    return TOKEN.sub(r"\2", body)


def shown(body: str) -> str:
    return TOKEN.sub(lambda m: f"{m[1]} [CROSS OUT, then write: {m[2]}]", body)


def info(t, layout):
    lay = layout[t["id"]]
    cpl = cpl_for(lay, t["lang"])
    n = len(wrap_lines(final(t["body"]), cpl))
    assert n <= len(lay["rules"]), (t["id"], n, len(lay["rules"]))
    words = len(final(t["body"]).split())
    assert 60 <= words <= 160, (t["id"], words)
    sheet = f"sheets/{t['id']}_{t['design']}.pdf"
    return lay, n, words, sheet


def extras(t) -> list[str]:
    ex = []
    m = TOKEN.search(t["body"])
    if m:
        ex.append(f'CROSSED-OUT CORRECTION: write "{m[1]}" as printed in the text, draw ONE straight line through it, '
                  f'and write "{m[2]}" just above it, between the lines. The corrected value is "{m[2]}".')
    if t.get("margin_note"):
        mn = t["margin_note"]
        ex.append(f'MARGIN NOTE: {mn["where"]}, write these {len(mn["lines"])} short lines, small and slightly slanted, '
                  f'like a quick note: ' + " / ".join(mn["lines"]))
    if t.get("extra"):
        ex.append(t["extra"])
    return ex


def md_block(text: str, ar: bool) -> str:
    if ar:
        return '<div dir="rtl" lang="ar">\n' + "<br>\n".join(text.split("\n")) + "\n</div>\n"
    return "```text\n" + text + "\n```\n"


def write_md(layout):
    L = ["# Texts to write by hand", "",
         "Copy each text onto its prepared sheet (PDF in `sheets/`). Write the BODY only; the printed title and `Ref:` stay untouched. "
         "Write naturally, in your own handwriting. You do not have to copy line breaks inside a paragraph, only where the text starts a new line. "
         "Line counts are estimates for normal handwriting. All names, numbers and organisations are invented. "
         "This file must NOT be uploaded.", "",
         "| Id | Sheet | Language | Dept | Words | About lines |", "| --- | --- | --- | --- | --- | --- |"]
    rows = []
    for t in TEXTS:
        lay, n, w, sheet = info(t, layout)
        rows.append((t, lay, n, w, sheet))
        L.append(f"| {t['id']} | `{sheet}` | {LANG[t['lang']]} | {DEPT[t['dept']]} | {w} | {n} |")
    for t, lay, n, w, sheet in rows:
        L += ["", f"## {t['id']} - {t['kind']}", "",
              f"- Paper: `{sheet}` (design `{t['design']}`, {DEPT[t['dept']]} version, printed Ref `{lay['ref']}`)",
              f"- Language: {LANG[t['lang']]}. About {w} words, about {n} lines of writing (blank lines between paragraphs included)."]
        if t.get("fields"):
            L += ["- Also fill the printed boxes at the top of the sheet:"] + [f"  - {k}: `{v}`" for k, v in t["fields"].items()]
        for e in extras(t):
            L.append(f"- {e}")
        L += ["", "Write this:", "", md_block(shown(t["body"]), t["lang"] != "en")]
    (OUT / "TEXTS_TO_WRITE.md").write_text("\n".join(L), encoding="utf-8")
    return rows


# ---------- large-type PDF ----------
def fnt(size, bold=False, ar=False, serif=False):
    n = ("DejaVuSerif" if serif and not ar else "DejaVuSans") + ("-Bold" if bold else "") + ".ttf"
    return ImageFont.truetype(str(FD / n), size, layout_engine=ImageFont.Layout.RAQM)


class Doc:
    M = 90

    def __init__(self):
        self.pages: list[Image.Image] = []
        self.new()

    def new(self):
        self.im = Image.new("RGB", SIZE, "white")
        self.d = ImageDraw.Draw(self.im)
        self.y = self.M
        self.pages.append(self.im)
        self.d.text((SIZE[0] // 2, SIZE[1] - 50), f"Texts to write - page {len(self.pages)}", font=fnt(22), fill=(120, 120, 120), anchor="mm")

    def need(self, h):
        if self.y + h > SIZE[1] - 110:
            self.new()

    def para(self, text, size=40, bold=False, fill=(20, 20, 20), gap=1.45, indent=0):
        ar = has_ar(text)
        f = fnt(size, bold, ar, serif=True)
        kw = {"direction": "rtl", "language": "ar"} if ar else {}
        width = SIZE[0] - 2 * self.M - indent
        lines, cur = [], ""
        for w in text.split(" "):
            t = (cur + " " + w).strip()
            if cur and f.getlength(t, **kw) > width:
                lines.append(cur)
                cur = w
            else:
                cur = t
        lines.append(cur)
        step = int(size * gap)
        self.need(step * min(len(lines), 3))
        for ln in lines:
            self.need(step)
            if ar:
                self.d.text((SIZE[0] - self.M, self.y), ln, font=f, fill=fill, anchor="ra", **kw)
            else:
                self.d.text((self.M + indent, self.y), ln, font=f, fill=fill)
            self.y += step

    def body(self, text):
        for ln in text.split("\n"):
            if ln.strip():
                self.para(ln, 40)
            else:
                self.y += 24


def write_pdf(rows):
    doc = Doc()
    doc.para("TEXTS TO WRITE BY HAND", 54, True)
    doc.para("Copy each text onto its prepared sheet. Write only the body. Leave the printed title and Ref alone. "
             "Write naturally. Do not upload this file.", 30)
    doc.y += 20
    for t, lay, n, w, sheet in rows:
        doc.need(420)
        doc.d.rectangle([doc.M, doc.y, SIZE[0] - doc.M, doc.y + 4], fill=(24, 52, 92))
        doc.y += 18
        doc.para(f"{t['id']}  {t['kind']}", 36, True, (24, 52, 92))
        doc.para(f"Paper: {sheet}  |  {LANG[t['lang']]}  |  {DEPT[t['dept']]}  |  about {n} lines", 26, fill=(80, 80, 80))
        for k, v in (t.get("fields") or {}).items():
            doc.need(60)
            doc.d.text((doc.M, doc.y + 6), f"{k}:", font=fnt(28, True), fill=(80, 80, 80))
            if has_ar(v):
                doc.d.text((SIZE[0] - doc.M, doc.y), v, font=fnt(38, ar=True), fill=(20, 20, 20), anchor="ra", direction="rtl", language="ar")
            else:
                doc.d.text((doc.M + 260, doc.y), v, font=fnt(38, serif=True), fill=(20, 20, 20))
            doc.y += 62
        for e in extras(t):
            doc.para(e, 28, True, (160, 30, 30))
        doc.y += 12
        doc.body(shown(t["body"]))
        doc.y += 40
    doc.pages[0].save(OUT / "TEXTS_TO_WRITE.pdf", "PDF", resolution=150.0, save_all=True, append_images=doc.pages[1:], quality=80)
    return len(doc.pages)


def write_key(rows):
    L = ["# Answer key (ground truth)", "",
         "Exact text of every item as it should read once written. What a reader sees can differ in spelling of digits, "
         "punctuation and line breaks; compare values, not layout. For crossed-out items the intended final value is given. "
         "Do NOT upload this file.", ""]
    for t, lay, n, w, sheet in rows:
        L += [f"## {t['id']} - {t['kind']}", "", f"Sheet `{sheet}`, Ref `{lay['ref']}`, title `{lay['title']}`, {DEPT[t['dept']]}.", ""]
        if t.get("fields"):
            L += ["Printed boxes:"] + [f"- {k}: {v}" for k, v in t["fields"].items()] + [""]
        L += ["Body:", "", "```text", final(t["body"]), "```", ""]
        m = TOKEN.search(t["body"])
        if m:
            L += [f"Physical page: `{m[1]}` is struck through and `{m[2]}` is written above it. Intended value: **{m[2]}**.", ""]
        if t.get("margin_note"):
            L += ["Margin note (not part of the body): `" + " ".join(t["margin_note"]["lines"]) + "`", ""]
    (OUT / "answer_key.md").write_text("\n".join(L), encoding="utf-8")


def write_questions():
    ids = {t["id"] for t in TEXTS}
    L = ["# Test questions", "",
         "Upload one dossier (see README), wait for `completed`, then ask these in the chat. Questions in Arabic over English documents and the reverse are on purpose. "
         "Kinds: numeric, correction (the corrected value is the answer), none (not answerable: the system must say it cannot find it).", ""]
    for g, members in GROUPS.items():
        assert DOSSIER_ID_RE.match(g), g
        assert set(members) <= ids
        L += [f"## Dossier `{g}` ({', '.join(members)})", ""]
        for i, (gg, ql, q, a, kind, src) in enumerate([x for x in QUESTIONS if x[0] == g], 1):
            L += [f"{i}. [{ql}, {kind}] {q}", f"   - Expected: {a}", f"   - Source: {src}"]
        L.append("")
    for g in GROUPS:
        qs = [x for x in QUESTIONS if x[0] == g]
        assert 3 <= len(qs) <= 5 and any(x[4] == "none" for x in qs), g
    assert any(x[4] == "correction" for x in QUESTIONS)
    (OUT / "questions.md").write_text("\n".join(L), encoding="utf-8")


def main():
    layout = json.loads((OUT / "paper" / "layout.json").read_text())
    rows = write_md(layout)
    pages = write_pdf(rows)
    write_key(rows)
    write_questions()
    print(f"{len(rows)} texts, TEXTS_TO_WRITE.pdf {pages} pages")


if __name__ == "__main__":
    main()
