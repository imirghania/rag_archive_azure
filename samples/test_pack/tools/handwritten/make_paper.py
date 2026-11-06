"""Blank official paper for handwritten tests: 11 designs (generic) plus one prepared sheet per text (own title and Ref).
Run: uv run python samples/test_pack/tools/handwritten/make_paper.py   (deterministic PNG; PDFs carry a timestamp)"""
from __future__ import annotations

import json
from pathlib import Path

from paperlib import (GREEN, INK, LIGHT, MID, NAVY, P, RED, RULE, RULE_D, TEAL, W, X0, X1, Sheet)
from texts_data import TEXTS

OUT = Path(__file__).resolve().parents[2] / "handwritten"
CO = dict(en="Harbourline Trading Co. Ltd.", ar="شركة هاربورلاين للتجارة المحدودة", addr_en="14 Quay Street, Port District, Hamra Bay",
          addr_ar="١٤ شارع الرصيف، حي المرفأ، خليج حمراء", tel="Tel +00 21 555 0142")
DEPT = {"FIN": dict(en="Finance Department", ar="إدارة الشؤون المالية", acc=NAVY, mail="accounts@harbourline.example"),
        "HR": dict(en="Human Resources Department", ar="إدارة الموارد البشرية", acc=GREEN, mail="hr@harbourline.example")}
BOTTOM = 3250


def footer(s, p, lines_en, lines_ar=None, y=3290, x0=X0, x1=X1):
    s.hline(x0, x1, y, fill=RULE_D, w=3)
    s.t(x0, y + 20, lines_en[0], 25, fill=MID)
    s.t(x0, y + 60, lines_en[1], 25, fill=MID)
    if lines_ar:
        s.t(x1, y + 14, lines_ar[0], 28, fill=MID, anchor="ra", ar=True)
        s.t(x1, y + 56, lines_ar[1], 28, fill=MID, anchor="ra", ar=True)


def co_footer(s, p, ar=False, bi=False, **kw):
    dp = DEPT[p["dept"]]
    en = [f"{CO['en']}  |  {CO['addr_en']}  |  {CO['tel']}  |  {dp['mail']}", f"{dp['en']}  |  Form {p['code']}  |  Page 1 of 1"]
    if bi:
        en = [f"{CO['en']}  |  {CO['tel']}", f"{dp['en']}  |  Form {p['code']}  |  Page 1 of 1"]
    arb = [f"{CO['ar']}  |  {CO['addr_ar']}", f"{dp['ar']}  |  نموذج رقم {p['code'][-2:]}"]
    if ar:  # Arabic sheet: Arabic right, short Latin contact left
        s.hline(X0, X1, 3290, fill=RULE_D, w=3)
        s.t(X0, 3310, f"{CO['tel']}  |  {dp['mail']}", 25, fill=MID)
        s.t(X0, 3350, f"Form {p['code']}  |  Page 1 of 1", 25, fill=MID)
        s.t(X1, 3304, arb[0], 28, fill=MID, anchor="ra", ar=True)
        s.t(X1, 3346, arb[1], 28, fill=MID, anchor="ra", ar=True)
    else:
        footer(s, p, en, arb if bi else None, **kw)


def title_ref(s, y, p, rtl=False, titles=True):
    """Pre-printed capital title and Ref line. Returns y where the next block may start."""
    acc = s.acc
    if p["title_ar"]:
        s.t(W // 2, y, p["title_ar"], 70, bold=True, fill=acc, anchor="ma", ar=True)
        s.t(W // 2, y + 100, p["title"], 44, bold=True, fill=MID, anchor="ma")
        y2 = y + 170
    else:
        s.t(W // 2, y, p["title"], 64, bold=True, fill=acc, anchor="ma")
        y2 = y + 95
    s.t(X1 if rtl else X0, y2 + 25, f"Ref: {p['ref']}", 38, mono=True, anchor="ra" if rtl else "la")
    return y2 + 100


def letter_head(s, p, kind):
    dp = DEPT[p["dept"]]
    acc = dp["acc"]
    if kind == "en":
        s.logo(X0 + 100, 235, 100, "HL")
        s.t(X0 + 250, 140, "HARBOURLINE", 80, bold=True, fill=acc)
        s.t(X0 + 254, 240, "TRADING CO. LTD.", 36, fill=TEAL)
        s.t(X0 + 254, 295, dp["en"], 34, bold=True, fill=MID)
        for i, tx in enumerate((CO["addr_en"], CO["tel"], dp["mail"])):
            s.t(X1, 165 + 46 * i, tx, 28, fill=MID, anchor="ra")
    elif kind == "ar":
        s.logo(X1 - 100, 235, 100, "HL")
        s.t(X1 - 250, 140, CO["ar"], 62, bold=True, fill=acc, anchor="ra", ar=True)
        s.t(X1 - 250, 245, dp["ar"], 44, fill=MID, anchor="ra", ar=True)
        s.t(X0, 150, CO["addr_ar"], 28, fill=MID, ar=True)
        for i, tx in enumerate((CO["tel"], dp["mail"])):
            s.t(X0, 205 + 46 * i, tx, 28, fill=MID)
    else:  # bilingual
        s.logo(W // 2, 215, 85, "HL")
        s.t(X0, 130, "HARBOURLINE", 64, bold=True, fill=acc)
        s.t(X0 + 2, 210, "TRADING CO. LTD.", 32, fill=TEAL)
        s.t(X0 + 2, 255, dp["en"], 30, bold=True, fill=MID)
        s.t(X1, 120, CO["ar"], 46, bold=True, fill=acc, anchor="ra", ar=True)
        s.t(X1, 205, dp["ar"], 38, fill=MID, anchor="ra", ar=True)
        s.t(W // 2, 325, f"{CO['addr_en']}  |  {CO['tel']}  |  {dp['mail']}", 26, fill=MID, anchor="ma")
    s.hline(X0, X1, 375 if kind != "bi" else 385, fill=acc, w=8)
    s.hline(X0, X1, 392 if kind != "bi" else 402, fill=TEAL, w=3)


def d_letter(kind):
    def fn(s, p):
        letter_head(s, p, kind)
        rtl = kind == "ar"
        y = title_ref(s, 450, p, rtl=rtl)
        rl = s.rules(X0, X1, y, BOTTOM)
        co_footer(s, p, ar=rtl, bi=kind == "bi")
        return dict(rules=rl, x0=X0, x1=X1, rtl=rtl)
    return fn


def small_head(s, p, rtl=False):
    dp = DEPT[p["dept"]]
    cx = X1 - 60 if rtl else X0 + 60
    s.logo(cx, 170, 60, "HL")
    if rtl:
        s.t(X1 - 150, 120, CO["ar"], 46, bold=True, fill=s.acc, anchor="ra", ar=True)
        s.t(X1 - 150, 190, dp["ar"], 34, fill=MID, anchor="ra", ar=True)
        s.t(X0, 130, "HARBOURLINE", 34, bold=True, fill=s.acc)
    else:
        s.t(X0 + 150, 115, "HARBOURLINE", 56, bold=True, fill=s.acc)
        s.t(X0 + 152, 190, f"Trading Co. Ltd.  |  {dp['en']}", 30, fill=MID)
    s.hline(X0, X1, 270, fill=s.acc, w=7)
    s.hline(X0, X1, 285, fill=TEAL, w=3)


def d_memo(rtl):
    def fn(s, p):
        small_head(s, p, rtl)
        by = 330
        bh = 250 if p["title_ar"] else 160
        s.rect(X0, by, X1, by + bh, fill=LIGHT, outline=s.acc, w=4)
        if p["title_ar"]:
            s.t(W // 2, by + 28, p["title_ar"], 70, bold=True, fill=s.acc, anchor="ma", ar=True)
            s.t(W // 2, by + 140, p["title"], 46, bold=True, fill=MID, anchor="ma")
        else:
            s.t(W // 2, by + 48, p["title"], 66, bold=True, fill=s.acc, anchor="ma")
        ry = by + bh + 25
        s.t(X1 if rtl else X0, ry, f"Ref: {p['ref']}", 38, mono=True, anchor="ra" if rtl else "la")
        y = ry + 85
        labels = [("TO", "إلى"), ("FROM", "من"), ("DATE", "التاريخ"), ("SUBJECT", "الموضوع")]
        fields = {}
        for en, ar in labels:
            lx0, lx1 = (X1 - 300, X1) if rtl else (X0, X0 + 300)
            fx0, fx1 = (X0, X1 - 300) if rtl else (X0 + 300, X1)
            s.rect(lx0, y, lx1, y + 100, fill=LIGHT)
            if rtl:
                s.t(lx1 - 20, y + 12, ar + ":", 42, bold=True, anchor="ra", ar=True)
                s.t(lx1 - 20, y + 66, en, 22, fill=MID, anchor="ra")
            else:
                s.t(lx0 + 20, y + 24, en + ":", 42, bold=True)
            s.rect(fx0, y, fx1, y + 100)
            fields[en] = [fx0 + 20, fx1 - 20, y + 80]
            y += 100
        rl = s.rules(X0, X1, y + 30, BOTTOM)
        co_footer(s, p, ar=rtl)
        return dict(rules=rl, x0=X0, x1=X1, rtl=rtl, fields=fields)
    return fn


def d_gov(s, p):
    s.crest(W // 2, 215, 100)
    s.t(X0, 125, "REPUBLIC OF SARVANIA", 38, bold=True, fill=INK)
    s.t(X0, 180, "MINISTRY OF MUNICIPAL SERVICES", 34, bold=True, fill=s.acc)
    s.t(X0, 232, "Directorate of Revenue and Fees", 30, fill=MID)
    s.t(X1, 110, "جمهورية سارفانيا", 44, bold=True, anchor="ra", ar=True)
    s.t(X1, 175, "وزارة الخدمات البلدية", 42, bold=True, fill=s.acc, anchor="ra", ar=True)
    s.t(X1, 240, "مديرية الإيرادات والرسوم", 34, fill=MID, anchor="ra", ar=True)
    s.hline(X0, X1, 360, fill=s.acc, w=8)
    s.hline(X0, X1, 377, fill=s.acc, w=3)
    y = title_ref(s, 420, p)
    fields = {}
    mid = W // 2
    for key, (a, b), en, ar in (("OUT_NO", (X0, mid - 20), "OUTGOING No.", "الرقم الصادر"), ("DATE", (mid + 20, X1), "DATE", "التاريخ")):
        fields[key] = list(s.cell(a, y, b, y + 140, en, ar))
    rl = s.rules(X0, X1, y + 190, BOTTOM)
    footer(s, p, ["Ministry of Municipal Services  |  Government Quarter, Al-Noor City  |  Tel +00 21 555 0300", "Directorate of Revenue and Fees  |  Form MSM-02  |  Page 1 of 1"],
           ["وزارة الخدمات البلدية  |  الحي الحكومي، مدينة النور", "مديرية الإيرادات والرسوم  |  نموذج رقم 02"])
    return dict(rules=rl, x0=X0, x1=X1, rtl=False, fields=fields)


def d_voucher(s, p):
    dp = DEPT[p["dept"]]
    s.logo(X0 + 60, 170, 60, "HL")
    s.t(X0 + 150, 115, "HARBOURLINE", 56, bold=True, fill=s.acc)
    s.t(X0 + 152, 190, f"Trading Co. Ltd.  |  {dp['en']}", 30, fill=MID)
    s.t(X1, 100, "No. 004217", 72, bold=True, fill=RED, anchor="ra", mono=True)
    s.t(X1, 195, "ORIGINAL - printed serial", 24, fill=MID, anchor="ra")
    s.hline(X0, X1, 270, fill=s.acc, w=7)
    s.hline(X0, X1, 285, fill=TEAL, w=3)
    y = title_ref(s, 320, p)
    fields = {}
    gap = 20
    lx1 = 1080
    fields["DATE"] = list(s.cell(X0, y, lx1, y + 120, "DATE", "التاريخ"))
    fields["PAID_TO"] = list(s.cell(X0, y + 130, lx1, y + 250, "PAY TO", "يصرف إلى"))
    ax0 = lx1 + gap
    s.rect(ax0, y, X1, y + 250, outline=s.acc, w=5)
    s.t(ax0 + 16, y + 10, "AMOUNT (USD)", 26, bold=True, fill=MID)
    s.t(X1 - 16, y + 6, "المبلغ", 30, fill=MID, anchor="ra", ar=True)
    fields["AMOUNT"] = [ax0 + 20, X1 - 20, y + 215]
    y2 = y + 270
    fields["WORDS"] = list(s.cell(X0, y2, X1, y2 + 125, "THE SUM OF (in words)", "مبلغ وقدره"))
    y3 = y2 + 150
    s.t(X0, y3, "BEING PAYMENT OF", 28, bold=True, fill=MID)
    s.t(X1, y3 - 6, "وذلك عن", 32, fill=MID, anchor="ra", ar=True)
    rl = s.rules(X0, X1, y3 + 20, y3 + 20 + 17 * P)
    sy = rl[-1] + 170
    for i, (en, ar) in enumerate((("PREPARED BY", "أعده"), ("APPROVED BY", "اعتمده"), ("RECEIVED BY", "المستلم"))):
        a = X0 + i * 680
        s.hline(a, a + 600, sy, fill=RULE_D, w=3)
        s.t(a, sy + 12, en, 24, bold=True, fill=MID)
        s.t(a + 600, sy + 8, ar, 28, fill=MID, anchor="ra", ar=True)
    co_footer(s, p, bi=True)
    return dict(rules=rl, x0=X0, x1=X1, rtl=False, fields=fields)


def d_formal(s, p):
    dp = DEPT[p["dept"]]
    s.t(X0, 120, "HARBOURLINE TRADING CO. LTD.", 44, bold=True, fill=s.acc)
    s.t(X0, 182, dp["en"], 30, fill=MID)
    s.t(X1, 135, "Formal correspondence sheet", 28, fill=MID, anchor="ra")
    s.hline(X0, X1, 250, fill=s.acc, w=6)
    y = title_ref(s, 295, p)
    mx = 1850
    top = y + 20
    s.d.line([(mx, top), (mx, BOTTOM)], fill=(228, 175, 175), width=3)
    s.d.line([(mx + 9, top), (mx + 9, BOTTOM)], fill=(228, 175, 175), width=3)
    s.t((mx + X1) // 2 + 10, top + 8, "MARGIN NOTES", 24, bold=True, fill=(150, 150, 150), anchor="ma")
    rl = s.rules(X0, mx - 20, top + 30, BOTTOM)
    co_footer(s, p)
    return dict(rules=rl, x0=X0, x1=mx - 20, rtl=False, margin=[mx + 30, X1])


def d_cert(s, p):
    a = s.acc
    s.rect(110, 110, W - 110, 3398, outline=a, w=9)
    s.rect(140, 140, W - 140, 3368, outline=a, w=2)
    for cx, cy in ((110, 110), (W - 110, 110), (110, 3398), (W - 110, 3398)):
        s.d.rectangle([cx - 28, cy - 28, cx + 28, cy + 28], fill="white", outline=a, width=6)
        s.star(cx, cy, 20, a)
    s.crest(W // 2, 320, 80)
    s.t(W // 2, 445, "HARBOURLINE TRADING CO. LTD.", 34, bold=True, fill=MID, anchor="ma")
    y = title_ref(s, 520, p)
    x0, x1 = 340, W - 340
    rl = s.rules(x0, x1, y + 10, 2950)
    sy = rl[-1] + 190
    s.hline(x0, x0 + 700, sy, fill=RULE_D, w=3)
    s.t(x0, sy + 12, "AUTHORISED SIGNATURE", 24, bold=True, fill=MID)
    s.hline(x0 + 800, x0 + 1100, sy, fill=RULE_D, w=3)
    s.t(x0 + 800, sy + 12, "DATE", 24, bold=True, fill=MID)
    s.d.ellipse([x1 - 250, sy - 200, x1, sy + 50], outline=RULE_D, width=3)
    s.t(x1 - 125, sy - 75, "STAMP", 26, fill=RULE_D, anchor="mm")
    dp = DEPT[p["dept"]]
    s.hline(x0, x1, 3270, fill=RULE_D, w=3)
    s.t(x0, 3290, f"{CO['en']}  |  {CO['addr_en']}  |  {CO['tel']}", 25, fill=MID)
    s.t(x0, 3328, f"{dp['en']}  |  Form {p['code']}  |  Page 1 of 1", 25, fill=MID)
    return dict(rules=rl, x0=x0, x1=x1, rtl=False)


def d_minutes(s, p):
    small_head(s, p)
    y = title_ref(s, 320, p) - 20
    fields = {}
    mid = W // 2
    fields["DATE"] = list(s.cell(X0, y, mid - 10, y + 125, "DATE", "التاريخ"))
    fields["TIME"] = list(s.cell(mid + 10, y, X1, y + 125, "TIME", "الوقت"))
    fields["VENUE"] = list(s.cell(X0, y + 140, X1, y + 265, "VENUE", "المكان"))
    fields["ATTENDEES"] = list(s.cell(X0, y + 280, X1, y + 405, "ATTENDEES", "الحضور"))
    y4 = y + 450
    s.t(X0, y4, "DISCUSSION AND ACTION ITEMS", 28, bold=True, fill=MID)
    s.t(X1, y4 - 6, "المناقشة وبنود العمل", 32, fill=MID, anchor="ra", ar=True)
    rl = s.rules(X0, X1, y4 + 20, BOTTOM)
    co_footer(s, p, bi=True)
    return dict(rules=rl, x0=X0, x1=X1, rtl=False, fields=fields)


def d_hr(s, p):
    letter_head(s, p, "en")
    s.d.rectangle([60, 90, 92, 392], fill=s.acc)
    s.rect(X1 - 520, 300, X1, 350, outline=s.acc, w=3)
    s.t(X1 - 260, 311, "CONFIDENTIAL - PERSONNEL", 24, bold=True, fill=s.acc, anchor="ma")
    y = title_ref(s, 450, p)
    rl = s.rules(X0, X1, y, BOTTOM)
    co_footer(s, p)
    return dict(rules=rl, x0=X0, x1=X1, rtl=False)


# name: (function, code, EN title, AR title, default dept)
DESIGNS = {
    "letterhead_en": (d_letter("en"), "LTR-01", "OFFICIAL LETTER", None, "FIN"),
    "letterhead_ar": (d_letter("ar"), "LTR-02", "OFFICIAL LETTER", "خطاب رسمي", "FIN"),
    "letterhead_bi": (d_letter("bi"), "LTR-03", "OFFICIAL LETTER", "خطاب رسمي", "FIN"),
    "memo_en": (d_memo(False), "MEM-01", "INTERNAL MEMORANDUM", None, "FIN"),
    "memo_ar": (d_memo(True), "MEM-02", "INTERNAL MEMORANDUM", "مذكرة داخلية", "FIN"),
    "gov": (d_gov, "MSM-02", "OFFICIAL CORRESPONDENCE", "مراسلة رسمية", "FIN"),
    "voucher": (d_voucher, "VCH-01", "PAYMENT VOUCHER", "سند صرف", "FIN"),
    "formal_ruled": (d_formal, "FRM-01", "FORMAL CORRESPONDENCE", None, "FIN"),
    "certificate": (d_cert, "CRT-01", "CERTIFICATE OF STATEMENT", None, "FIN"),
    "minutes": (d_minutes, "MIN-01", "MINUTES OF MEETING", "محضر اجتماع", "FIN"),
    "hr_employment": (d_hr, "HRL-01", "EMPLOYMENT LETTER", None, "HR"),
}


def build(design, dept, ref, title=None, title_ar="-"):
    fn, code, t_en, t_ar, _ = DESIGNS[design]
    p = dict(dept=dept, ref=ref, code=code, title=title or t_en, title_ar=(t_ar if title_ar == "-" else title_ar) if t_ar else None)
    s = Sheet(DEPT[dept]["acc"])
    lay = fn(s, p)
    lay.update(design=design, ref=ref, title=p["title"], dept=dept)
    return s.im, lay


def save(im, stem: Path):
    stem.parent.mkdir(parents=True, exist_ok=True)
    im.save(stem.with_suffix(".png"), optimize=True, dpi=(300, 300))
    im.save(stem.with_suffix(".pdf"), "PDF", resolution=300.0, quality=80)


def main():
    layout = {}
    for name, (_, code, _, _, dept) in DESIGNS.items():
        im, lay = build(name, dept, f"{dept}-{code[:3]}-0001")
        save(im, OUT / "paper" / f"blank_{name}")
        layout[f"paper/blank_{name}"] = lay
    for t in TEXTS:
        dept = t["dept"]
        code = DESIGNS[t["design"]][1]
        ref = f"{dept}-{code[:3]}-{1000 + t['n']}"
        im, lay = build(t["design"], dept, ref, t["title"], t.get("title_ar", "-"))
        save(im, OUT / "sheets" / f"{t['id']}_{t['design']}")
        layout[t["id"]] = lay
    (OUT / "paper" / "layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=1))
    for k, v in layout.items():
        if k.startswith("HW"):
            assert len(v["rules"]) >= 8, k
    print(f"{len(DESIGNS)} designs, {len(TEXTS)} prepared sheets")


if __name__ == "__main__":
    main()
