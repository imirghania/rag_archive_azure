"""job-reconcile: decides each line with rule set 1 (two readers), anchors margin notes and assembles the page
(spec, Workflow 1, Step 6)."""
from __future__ import annotations

import re
import unicodedata

from docai.contracts import keys, messageids
from docai.contracts.artifacts import (
    Box,
    Line,
    LinesFile,
    OcrResult,
    ReadingEntry,
    Readings,
    Triage,
    VlmReading,
)
from docai.contracts.enums import PAGE_FINAL, TaskReason, TrustTier
from docai.contracts.messages import Envelope, ReconcileRequested, parse_payload
from docai.documents.artifactio import read_model, write_model
from docai.documents.linetext import paragraphs, render_markdown
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send

_EASTERN = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")} | {ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")}
_SEPARATORS = {ord("٬"): ",", ord("٫"): ".", ord("،"): ","}
_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ئ": "ي", "ؤ": "و", "ة": "ه"})


def normalize(text: str) -> str:
    """Case and spacing are ignored; Arabic diacritics are dropped and alef/hamza/ya forms unified; Eastern-Arabic and
    Persian digits become 0-9 and Arabic separators become , and . Digits and separators must then match exactly."""
    t = text.translate(_EASTERN).translate(_SEPARATORS)
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c) or c in "́")
    t = re.sub(r"[ً-ٰٟـ]", "", t).translate(_ALEF)
    return re.sub(r"\s+", "", t).casefold()


def anchor_margin_notes(lines: list[Line]) -> list[Line]:
    """A handwritten line wholly right of the printed column is a margin note. It is anchored to the paragraph whose
    vertical span it overlaps most; the note directly below another margin note joins it (spec: how the margin note is anchored)."""
    printed = [ln for ln in lines if ln.style == "printed" and ln.text.strip()]
    if not printed:
        return lines
    col_right = max(ln.box.x1 for ln in printed)
    for ln in lines:
        ln.placement = "right_margin" if ln.style == "handwritten" and ln.box.x0 > col_right else "main"
    paras = paragraphs([ln.model_copy(update={"placement": "main"}) for ln in lines if ln.style == "printed" or ln.placement == "main"])
    spans = [(Box(x0=min(l.box.x0 for l in p), y0=min(l.box.y0 for l in p), x1=max(l.box.x1 for l in p), y1=max(l.box.y1 for l in p)), f"P{i}")
             for i, p in enumerate(paras, start=1)]
    for p_i, p in enumerate(paras, start=1):
        for l in p:
            for orig in lines:
                if orig.id == l.id:
                    orig.paragraph = f"P{p_i}"
    prev: Line | None = None
    for ln in sorted((l for l in lines if l.placement == "right_margin"), key=lambda l: l.box.y0):
        if prev and ln.box.y0 - prev.box.y1 <= 1.5 * max(ln.box.height, 1) and prev.anchor:
            ln.anchor = prev.anchor  # initials under a note form one note with it
        elif spans:
            best = max(spans, key=lambda s: (ln.box.overlap_y(s[0]), -abs((ln.box.y0 + ln.box.y1) / 2 - (s[0].y0 + s[0].y1) / 2)))
            ln.anchor = best[1]
        prev = ln
    return lines


def decide_line(ocr_text: str, ocr_conf: float, second: str | None, *, min_vote: float, from_text_layer: bool, style: str, printed_floor: float):
    """Rule set 1. Returns (tier, final_text, candidates, source)."""
    if from_text_layer:
        return TrustTier.digital_source, ocr_text, [], "text_layer"
    if second is None:  # never second-read: printed and confident
        return TrustTier.printed_high_conf, ocr_text, [], "ocr"
    ocr_votes = ocr_conf >= min_vote
    if ocr_votes and normalize(ocr_text) == normalize(second):
        # a low-confidence printed line that the second reader confirms is still a printed line (rank 5, not 3)
        tier = TrustTier.printed_high_conf if style == "printed" else TrustTier.handwritten_dual_agreed
        return tier, second, [], "second_reader"
    cands = [ocr_text, second] if ocr_votes else [second]
    return TrustTier.unverified, second if not ocr_votes else ocr_text, cands, "ocr"


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, ReconcileRequested)
    dossier_id, rev = revision_of(env)
    pref = keys.PageRef.parse(env.subject)
    dept = keys.department_of(dossier_id)
    tun = ctx.settings.tuning
    if ctx.ops.get_page(dossier_id, rev, pref.page_no).status in PAGE_FINAL:
        return

    ocr = read_model(ctx.blobs, "extracted", pref.dir + "ocr.json", OcrResult)
    triage = read_model(ctx.blobs, "extracted", pref.dir + "triage.json", Triage)
    crops = {t.id: t for t in triage.lines}
    readings: dict[str, VlmReading] = {}
    for lid, path in req.second_reads.items():
        r = read_model(ctx.blobs, "extracted", pref.dir + path, VlmReading)
        if r.crop_sha256 != crops[lid].crop_sha256:
            raise ValueError(f"{lid}: the reading was made from another crop than triage.json lists")  # abandoned and retried
        readings[lid] = r
    if len(readings) != req.expected_second_reads:
        raise ValueError(f"expected {req.expected_second_reads} second readings, found {len(readings)}")

    lines: list[Line] = []
    unverified: list[Line] = []
    for ol in ocr.lines:
        sec = readings.get(ol.id)
        tier, text, cands, source = decide_line(ol.text, ol.conf, sec.text if sec else None, min_vote=tun.reconcile_ocr_min_vote,
                                                from_text_layer=ol.from_text_layer, style=ol.style, printed_floor=tun.printed_second_read_below)
        line = Line(id=ol.id, text=text, tier=tier, style=ol.style, box=ol.box, lang=ol.lang, conf=ol.conf, source=source, candidates=cands)
        lines.append(line)
        if sec:  # the reviewer sees both readings
            write_model(ctx.blobs, "extracted", f"{pref.dir}{ol.id}.readings.json", Readings(
                line_key=keys.line_key(pref.key, ol.id), readings=[ReadingEntry(engine="ocr", text=ol.text, conf=ol.conf),
                                                                  ReadingEntry(engine="second_reader", text=sec.text)]))
        if tier is TrustTier.unverified:
            unverified.append(line)
    lines = anchor_margin_notes(lines)
    lf = LinesFile(page_key=pref.key, page_no=pref.page_no, version=1, page_width=ocr.page_width, page_height=ocr.page_height,
                   page_image_sha256=triage.page_image_sha256, lines=lines)
    write_model(ctx.blobs, "extracted", pref.dir + "lines.v1.json", lf)  # the base file: never edited
    ctx.blobs.write("extracted", pref.dir + "page.v1.md", render_markdown(lf).encode("utf-8"), overwrite=True)

    for ln in unverified:
        reason = TaskReason.readers_disagree if len(ln.candidates) == 2 else TaskReason.ocr_too_unsure
        ctx.ops.create_review_task(department=dept, dossier_id=dossier_id, revision=rev, page_no=pref.page_no, line_id=ln.id,
                                   line_key=keys.line_key(pref.key, ln.id), reason=reason.value)

    done = ctx.ops.finish_page(dossier_id, rev, pref.page_no, "reconciled")  # fan-in: counts this page exactly once
    if done and done[0] == done[1]:  # this execution closed the last page of the revision
        dkey = keys.dossier_key(dossier_id, rev)
        send(ctx, envelope("dossier.segment.requested", dkey, department=dept, dossier_id=dossier_id, revision=rev),
             message_id=messageids.message_id("segment", dkey))


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
