"""How an unverified line is written into text: only the disagreement is marked (spec, Step 6)."""
from __future__ import annotations

import difflib

from docai.contracts.artifacts import Line, LinesFile
from docai.contracts.enums import TrustTier


def mark_disagreement(candidates: list[str]) -> str:
    """Word-aligns two readings; words that agree are written normally and only the difference is marked."""
    if len(candidates) == 1:
        return f"[unverified: {candidates[0]}]"
    a, b = candidates[0].split(), candidates[1].split()
    out: list[str] = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            out += a[i1:i2]
        else:
            out.append(f"[unverified: {' '.join(a[i1:i2])} | {' '.join(b[j1:j2])}]")
    return " ".join(out)


def paragraphs(lines: list[Line]) -> list[list[Line]]:
    """Consecutive main-column lines belong to one paragraph until a vertical gap of more than 0.75 line heights."""
    main = [ln for ln in lines if ln.placement == "main"]
    paras: list[list[Line]] = []
    for ln in sorted(main, key=lambda l: (l.box.y0, l.box.x0)):
        if paras and ln.box.y0 - paras[-1][-1].box.y1 <= 0.75 * max(ln.box.height, 1) and ln.text.strip():  # a blank line is about one line height
            paras[-1].append(ln)
        elif ln.text.strip():
            paras.append([ln])
    return paras


def render_markdown(lf: LinesFile) -> str:
    """The page in reading order, with each margin note placed right after the paragraph it is anchored to."""
    by_para: dict[str, list[Line]] = {}
    for ln in lf.lines:
        if ln.placement != "main" and ln.anchor:
            by_para.setdefault(ln.anchor, []).append(ln)

    def text_of(ln: Line) -> str:
        return mark_disagreement(ln.candidates) if ln.tier is TrustTier.unverified and ln.candidates else ln.text

    out: list[str] = []
    paras = paragraphs(lf.lines)
    for i, p in enumerate(paras, start=1):
        body = " ".join(text_of(l) for l in p)
        first = p[0]
        if i == 1 and first.text.isupper() and len(p) == 1:
            out.append(f"## {body.title()}")
        else:
            out.append(body)
        notes = sorted(by_para.get(f"P{i}", []), key=lambda l: l.box.y0)
        for n, note in enumerate(notes):
            head = f"Margin note (handwritten, beside paragraph {i}): " if n == 0 else ""
            out.append(f"> {head}{text_of(note)}")
    stray = [l for l in lf.lines if l.placement != "main" and not l.anchor]
    for note in stray:
        out.append(f"> Page note (handwritten): {text_of(note)}")
    return "\n\n".join(out) + "\n"
