"""Drawing helpers for the blank official paper (A4, 300 dpi). Printed fonts only: no handwriting-like font."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 2480, 3508
P = 112  # ruled line pitch: 9.5 mm at 300 dpi
X0, X1 = 250, 2230
FD = Path("/usr/share/fonts/truetype/dejavu")
NAVY, GREEN, TEAL = (24, 52, 92), (0, 98, 84), (0, 120, 130)
INK, MID, RULE, RULE_D = (30, 30, 30), (95, 95, 95), (200, 200, 200), (170, 170, 170)
LIGHT, RED = (238, 241, 246), (170, 35, 35)

_cache: dict = {}


def font(size: int, bold=False, serif=False, mono=False) -> ImageFont.FreeTypeFont:
    key = (size, bold, serif, mono)
    if key not in _cache:
        name = ("DejaVuSerif" if serif else "DejaVuSansMono" if mono else "DejaVuSans") + ("-Bold" if bold else "") + ".ttf"
        _cache[key] = ImageFont.truetype(str(FD / name), size, layout_engine=ImageFont.Layout.RAQM)
    return _cache[key]


class Sheet:
    def __init__(self, acc):
        self.im = Image.new("RGB", (W, H), "white")
        self.d = ImageDraw.Draw(self.im)
        self.acc = acc

    def t(self, x, y, s, size=40, bold=False, fill=INK, anchor="la", ar=False, mono=False, serif=False) -> float:
        f = font(size, bold, serif and not ar, mono and not ar)
        kw = {"direction": "rtl", "language": "ar"} if ar else {}
        self.d.text((x, y), s, font=f, fill=fill, anchor=anchor, **kw)
        return f.getlength(s, **kw)

    def hline(self, x0, x1, y, fill=RULE, w=2):
        self.d.line([(x0, y), (x1, y)], fill=fill, width=w)

    def rect(self, x0, y0, x1, y1, fill=None, outline=RULE_D, w=2):
        self.d.rectangle([x0, y0, x1, y1], fill=fill, outline=outline, width=w)

    def rules(self, x0, x1, y0, y1) -> list[int]:
        """Light-grey writing rules, first baseline P below y0. Returns the baselines."""
        ys = list(range(y0 + P, y1 + 1, P))
        for y in ys:
            self.hline(x0, x1, y)
        return ys

    def logo(self, cx, cy, r, letters):
        d = self.d
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=self.acc)
        d.ellipse([cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10], outline="white", width=4)
        self.t(cx, cy - r * 0.05, letters, int(r * 0.85), bold=True, fill="white", anchor="mm", ar=any("؀" <= c <= "ۿ" for c in letters))
        d.arc([cx - r * 0.55, cy + r * 0.25, cx + r * 0.55, cy + r * 0.75], 20, 160, fill="white", width=5)

    def star(self, cx, cy, r, fill):
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.42
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.d.polygon(pts, fill=fill)

    def crest(self, cx, cy, r):
        for k, wd in ((0, 7), (14, 3), (r * 0.62, 2)):
            self.d.ellipse([cx - r + k, cy - r + k, cx + r - k, cy + r - k], outline=self.acc, width=int(wd))
        self.star(cx, cy, r * 0.42, self.acc)

    def cell(self, x0, y0, x1, y1, en, ar=None):
        """Bordered field cell with small bilingual label. Returns (field_x0, field_x1, baseline)."""
        self.rect(x0, y0, x1, y1)
        self.t(x0 + 14, y0 + 8, en, 24, bold=True, fill=MID)
        if ar:
            self.t(x1 - 14, y0 + 4, ar, 28, fill=MID, anchor="ra", ar=True)
        return (x0 + 20, x1 - 20, y1 - 22)


def has_ar(s: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in s)


def wrap_lines(text: str, cpl: int) -> list[str]:
    """Hand-writing line plan: source lines kept, long ones wrapped at `cpl` characters (word boundaries)."""
    import textwrap
    out: list[str] = []
    for ln in text.split("\n"):
        out += textwrap.wrap(ln, cpl, break_long_words=False) or [""]
    return out


def cpl_for(layout: dict, lang: str) -> int:
    """Characters per handwritten line: about 32 px per Latin character, 36 px per Arabic one, at 300 dpi."""
    return int((layout["x1"] - layout["x0"]) / (36 if lang in ("ar", "mixed") else 32))
