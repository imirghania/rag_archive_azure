"""Drawing toolkit for the printed handwriting forms: blank page, zones, simulated-handwriting preview.

Reuses the page size, fonts and the handwriting simulator of docai.devtools (samples.py, templates.py).
Every writing zone is declared once (position, language, what to write); the blank form, zones.json,
WHAT_TO_WRITE, the answer key and the preview all come from that one declaration.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from docai.devtools.samples import FONT_DIR, HAND, INK, SANS, H, Line, Page, W, _font, render_page
from docai.devtools.templates import GRAY_BOX, GRAY_LABEL, GRAY_RULE, Hand, _baseline_to_y

SANS_B = FONT_DIR / "dejavu/DejaVuSans-Bold.ttf"
L, R = 200, 2280  # content column
ROW = 110  # ruled line pitch in px: 9.3 mm
ORG_EN, ORG_AR = "Meridian Falak Group", "مجموعة ميريديان فلك"
ADDRESS = "Plot 24, Harbour Road, Port Meridian"


def has_ar(s: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in s)


def put(d: ImageDraw.ImageDraw, x: int, y: int, text: str, size: int = 34, bold: bool = False, anchor: str = "l",
        fill: int = INK) -> float:
    """Printed text on a baseline (y). Arabic runs are shaped by Raqm. Returns the text width."""
    kw = {"direction": "rtl", "language": "ar"} if has_ar(text) else {}
    f = _font(SANS_B if bold else SANS, size)
    d.text((x, y), text, font=f, fill=fill, anchor=anchor + "s", **kw)
    return f.getlength(text, **kw)


def width(text: str, size: int, bold: bool = False) -> float:
    kw = {"direction": "rtl", "language": "ar"} if has_ar(text) else {}
    return _font(SANS_B if bold else SANS, size).getlength(text, **kw)


# What to write, beyond a plain string / list of lines (one per ruled line) / None (leave empty).
@dataclass
class Cross:
    old: str
    new: str


@dataclass
class Tick:
    i: int


@dataclass
class Sig:
    pass


@dataclass
class Zone:
    id: str
    x0: int
    y0: int
    x1: int
    y1: int
    language: str  # en | ar | en+ar | digits
    purpose: str
    ruled_lines: list[int]
    kind: str  # text | checkbox | signature
    where: str
    write: object
    note: str = ""
    ticks: list[tuple[int, int]] = field(default_factory=list)
    options: list[str] = field(default_factory=list)
    size: int = 36


def pos(x0: int, y0: int, x1: int, y1: int) -> str:
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    v = "top" if cy < 900 else "upper" if cy < 1500 else "middle" if cy < 2200 else "lower" if cy < 2800 else "bottom"
    h = "full-width" if x1 - x0 > 1500 else "left" if cx < 900 else "right" if cx > 1580 else "centre"
    return f"{v} {h}"


class Form:
    def __init__(self, code: str, slug: str, title: str, ref: str, dept: str, lang: str, purpose: str, dossier: str,
            title_ar: str = "") -> None:
        self.code, self.slug, self.title, self.ref, self.dept, self.lang = code, slug, title, ref, dept, lang
        self.purpose, self.dossier, self.title_ar = purpose, dossier, title_ar
        self.rtl = lang == "ar"
        self.img = Image.new("L", (W, H), 255)
        self.d = ImageDraw.Draw(self.img)
        self.zones: list[Zone] = []
        self.low = 0  # lowest writing-area bottom so far; rows go downwards
        self.file = f"{code}_{slug}.pdf"
        self._header()
        self.y0 = 580 if self.rtl else 480

    # ---- header: logo block, organisation, capital-letter title, Ref line ----
    def _header(self) -> None:
        d, rtl = self.d, self.rtl
        lx = R - 110 if rtl else L
        d.rounded_rectangle((lx, 110, lx + 110, 220), 20, fill=70)
        put(d, lx + 55, 186, "MF", 46, True, "m", fill=255)
        d.ellipse((lx + 78, 120, lx + 100, 142), fill=255)
        if self.lang == "ar":
            put(d, lx - 30, 168, ORG_AR, 44, True, "r")
            put(d, lx - 30, 212, ADDRESS, 26, False, "r", 90)
        else:
            put(d, lx + 140, 168, ORG_EN, 44, True)
            put(d, lx + 140, 212, ADDRESS, 26, False, "l", 90)
            if self.lang == "bi":
                put(d, R, 168, ORG_AR, 44, True, "r")
        d.line((L, 260, R, 260), fill=GRAY_BOX, width=3)
        if self.lang == "ar":
            put(d, R, 350, self.title, 54, True, "r")
            put(d, R, 440, self.title_ar, 60, True, "r")
            put(d, R, 520, f"Ref: {self.ref}", 36, False, "r")
        else:
            put(d, L, 350, self.title, 60, True)
            if self.lang == "bi":
                put(d, R, 350, self.title_ar, 60, True, "r")
            put(d, L, 430, f"Ref: {self.ref}", 36)

    # ---- layout helpers ----
    def nx(self, b: int) -> int:
        """y of the next row: below the tallest area placed so far."""
        return max(b, self.low) + 75

    def cols(self, weights: list[float], gap: int = 50, x0: int = L, x1: int = R) -> list[tuple[int, int]]:
        """Column spans in reading order (right to left on Arabic forms)."""
        weights = weights[::-1] if self.rtl else weights  # laid out left to right, then flipped
        avail = x1 - x0 - gap * (len(weights) - 1)
        out, x = [], x0
        for w in weights:
            out.append((round(x), round(x + avail * w / sum(weights))))
            x += avail * w / sum(weights) + gap
        return out[::-1] if self.rtl else out

    def lab(self, x0: int, x1: int, y: int, en: str, ar: str, size: int = 30) -> None:
        if self.lang in ("en", "bi") and en:
            put(self.d, x0, y, en, size, False, "l")
        if self.lang in ("ar", "bi") and ar:
            put(self.d, x1, y, ar, size, False, "r")
        if self.lang == "bi" and en and ar:
            assert width(en, size) + width(ar, size) + 30 < x1 - x0, f"{self.code}: labels collide: {en} / {ar}"

    def _label_desc(self, en: str, ar: str) -> str:
        return en  # English gloss only: the "where" text is read in English even on Arabic forms

    def zone(self, x0: int, y0: int, x1: int, y1: int, lang: str, purpose: str, write: object, where: str, kind: str = "text",
            note: str = "", lines: int = 1, size: int = 36) -> Zone:
        z = Zone(f"Z{len(self.zones) + 1}", x0, y0, x1, y1, lang, purpose, [y0 + ROW * (i + 1) + 4 for i in range(lines)], kind,
                 where, write, note, size=size)
        if self.rtl:
            put(self.d, x1 - 8, y0 + 26, z.id, 24, False, "r", GRAY_LABEL)
        else:
            put(self.d, x0 + 8, y0 + 26, z.id, 24, False, "l", GRAY_LABEL)
        self.zones.append(z)
        return z

    def _lang(self, lang: str | None) -> str:
        return lang or ("ar" if self.rtl else "en")

    def field(self, x0: int, x1: int, y: int, en: str, ar: str, write: object, lang: str | None = None, lines: int = 1,
            style: str = "box", kind: str = "text", note: str = "", size: int = 36, where: str | None = None,
            purpose: str | None = None) -> int:
        """Label on baseline y, writing area below it. Returns the bottom of the area."""
        self.lab(x0, x1, y, en, ar)
        a, b = y + 14, y + 14 + ROW * lines + 20
        d = self.d
        if style == "box":
            d.rectangle((x0, a, x1, b), outline=GRAY_BOX, width=3)
        else:
            d.line((x0, b - 14, x1, b - 14), fill=GRAY_RULE, width=2)
        if lines > 1 and kind != "signature":
            for i in range(lines):
                d.line((x0 + 8, a + ROW * (i + 1) + 4, x1 - 8, a + ROW * (i + 1) + 4), fill=GRAY_RULE, width=2)
        desc = self._label_desc(en, ar)
        what = "line" if style != "box" else "box"
        self.zone(x0, a, x1, b, self._lang(lang), purpose or en, write, where or f'{pos(x0, a, x1, b)}, {what} under "{desc}"',
                  kind, note, lines, size)
        self.low = max(self.low, b)
        return b

    def checks(self, x0: int, x1: int, y: int, en: str, ar: str, options: list[tuple[str, str]], chosen: int, note: str = "",
            purpose: str | None = None) -> int:
        self.lab(x0, x1, y, en, ar)
        a, b = y + 14, y + 104
        d, rtl = self.d, self.rtl
        zone = self.zone(x0, a, x1, b, "en", purpose or en, Tick(chosen), "", "checkbox", note)
        cur = x1 - 80 if rtl else x0 + 80
        sx = -1 if rtl else 1
        d.rectangle((x0, a, x1, b), outline=GRAY_BOX, width=3)
        for oen, oar in options:
            bx = cur - 46 if rtl else cur
            cy = a + 52
            d.rectangle((bx, cy - 23, bx + 46, cy + 23), outline=INK, width=3)
            zone.ticks.append((bx + 23, cy))
            label = [t for t, ok in ((oen, self.lang in ("en", "bi")), (oar, self.lang in ("ar", "bi"))) if ok and t]
            cx = cur + sx * 62
            for t in label:
                w = put(d, cx, cy + 12, t, 32, False, "r" if rtl else "l")
                cx += sx * (w + 16)
            cur = cx + sx * 60
        zone.options = [(o[1] + f" ({o[0]})") if self.lang == "ar" else (f"{o[0]} / {o[1]}" if self.lang == "bi" else o[0]) for o in options]
        zone.where = f'{pos(x0, a, x1, b)}, row of checkboxes under "{self._label_desc(en, ar)}"'
        zone.language = "en"
        self.low = max(self.low, b)
        return b

    def table(self, y: int, name: str, cols: list[dict], rows: list[list[object]], note: dict | None = None) -> int:
        """cols: dict(en, ar, w, lang, [static: list of printed texts]); rows: one write spec per non-static column.
        Header row 100 px, body rows 130 px. Returns the table's bottom."""
        d = self.d
        spans = self.cols([c["w"] for c in cols], gap=0)
        hdr_h, row_h = 100, ROW + 20
        for c, (a, b) in zip(cols, spans):
            d.rectangle((a, y, b, y + hdr_h), fill=236, outline=GRAY_BOX, width=3)
            en, ar = c.get("en", ""), c.get("ar", "")
            lines = [t for t, ok in ((en, self.lang in ("en", "bi")), (ar, self.lang in ("ar", "bi"))) if ok and t]
            for i, t in enumerate(lines):
                yy = y + (hdr_h // 2 + 12 if len(lines) == 1 else 40 + 38 * i)
                put(d, (a + b) // 2, yy, t, 26 if len(lines) > 1 else 28, True, "m")
            assert max(width(t, 26, True) for t in lines) < b - a - 8, f"{self.code}: header too wide: {lines}"
        for r, row in enumerate(rows):
            top = y + hdr_h + r * row_h
            ci = 0
            for c, (a, b) in zip(cols, spans):
                d.rectangle((a, top, b, top + row_h), outline=GRAY_BOX, width=3)
                if "static" in c:
                    put(d, (a + b) // 2, top + 78, c["static"][r], 32, False, "m")
                    continue
                spec = row[ci]
                ci += 1
                label = c["en"] or c.get("ar", "")
                where = f'{name} table, row {r + 1}, "{label}" column'
                if "static" in cols[0] and cols[0]["static"][r]:
                    where += f' (row labelled "{cols[0]["static"][r]}")'
                self.zone(a, top, b, top + row_h, self._lang(c.get("lang")), f"{name} row {r + 1} {label}", spec,
                          f"{pos(a, top, b, top + row_h)}, {where}",
                          kind=c.get("kind", "text"), note=(note or {}).get((r, label), ""), size=c.get("size", 34))
        return y + hdr_h + len(rows) * row_h

    def text(self, x: int, y: int, text: str, size: int = 34, bold: bool = False, anchor: str = "l") -> None:
        put(self.d, x, y, text, size, bold, anchor)

    def para(self, y: int, text: str, size: int = 36, x0: int = L, x1: int = R, lh: int = 62) -> int:
        """Wrapped printed paragraph, right-aligned on Arabic forms. Returns the y after it."""
        rows, cur = [], ""
        for w in text.split():
            if cur and width(f"{cur} {w}", size) > x1 - x0:
                rows.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        rows.append(cur)
        for i, r in enumerate(rows):
            put(self.d, x1 if self.rtl else x0, y + lh * i, r, size, False, "r" if self.rtl else "l")
        return y + lh * len(rows)


# ------------------------------------------------------------------ preview (simulated handwriting)
INK_HAND = 40


def _hand_width(text: str, size: int) -> float:
    if has_ar(text):
        return _font(SANS, size + 6).getlength(text, direction="rtl", language="ar")
    return _font(HAND, size + 4).getlength(text)


def preview(form: Form, seed: int = 11) -> tuple[Image.Image, list[str]]:
    """The blank form with simulated handwriting in every zone. Returns the image and overflow warnings."""
    rng = random.Random(seed)
    hands: list[Line] = []
    post: list[tuple] = []
    warn: list[str] = []

    def place(z: Zone, text: str, i: int, x: int | None = None, right: bool = False) -> tuple[int, int]:
        lang = "ar" if has_ar(text) else "en"
        w = int(_hand_width(text, z.size))
        if x is None:
            x = z.x1 - 24 - w if right else z.x0 + 24
        if x < z.x0 + 6 or x + w > z.x1 - 6:
            warn.append(f"{form.code} {z.id}: '{text}' is {w}px, zone is {z.x1 - z.x0}px")
        y = _baseline_to_y(Hand(zone="", text=text, lang=lang, size=z.size), z.ruled_lines[i] - (20 if lang == "ar" else 8))
        hands.append(Line(x, y, text, "handwritten", lang, z.size, tilt=0.5))
        return x, w

    for z in form.zones:
        s = z.write
        if s is None:
            continue
        if isinstance(s, Tick):
            post.append(("tick", z.ticks[s.i]))
        elif isinstance(s, Sig):
            post.append(("sig", z))
        elif isinstance(s, Cross):
            right = form.rtl or has_ar(s.new)
            ow, nw = int(_hand_width(s.old, z.size)), int(_hand_width(s.new, z.size))
            ox = z.x1 - 24 - ow if right else z.x0 + 24
            place(z, s.old, 0, ox)
            nx = ox - 40 - nw if right else ox + ow + 40
            place(z, s.new, 0, nx)
            post.append(("cross", ox, z.ruled_lines[0] - 8, ow))
        else:
            for i, t in enumerate(s if isinstance(s, list) else [s]):
                place(z, t, i, right=has_ar(t))
    img, _ = render_page(Page(hands, "P"), seed, base=form.img.copy())
    d = ImageDraw.Draw(img)
    for p in post:
        if p[0] == "tick":
            cx, cy = p[1]
            d.line([(cx - 15, cy + 1), (cx - 4, cy + 15), (cx + 20, cy - 20)], fill=INK_HAND, width=6, joint="curve")
        elif p[0] == "cross":
            _, x, yb, w = p
            d.line((x - 6, yb - 12, x + w + 6, yb - 24), fill=INK_HAND, width=4)
        else:
            z = p[1]
            base = z.y1 - 60
            sgn = -1 if form.rtl else 1
            x = z.x1 - 70 if form.rtl else z.x0 + 70
            span = min(420, (z.x1 - z.x0) * 0.7) * rng.uniform(0.8, 1.0)
            freq, amp = rng.uniform(5, 11), min(55, (z.y1 - z.y0) * 0.4)
            pts = [(x + sgn * (k / 159) * span, base - amp * abs(math.sin((k / 159) * freq)) * (1 - 0.6 * k / 159) + rng.uniform(-3, 3))
                   for k in range(160)]
            d.line(pts, fill=INK_HAND, width=4, joint="curve")
            d.line((x - sgn * 15, base + 8, x + sgn * span, base - 4), fill=INK_HAND, width=3)
    return img, warn
