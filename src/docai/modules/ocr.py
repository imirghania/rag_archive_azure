"""job-ocr-online: reads a page with the OCR engine and triages its lines (spec, Workflow 1, Step 4)."""
from __future__ import annotations

import hashlib
import io

from PIL import Image

from docai.contracts import keys, messageids
from docai.contracts.artifacts import Box, OcrResult, Triage, TriageLine
from docai.contracts.enums import PAGE_FINAL, PageStatus
from docai.contracts.messages import Envelope, PageOcrRequested, parse_payload
from docai.documents.artifactio import read_model, write_model
from docai.ports import AlreadyExists
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send


def crop_box(box: Box, page_w: int, page_h: int, margin_ratio: float, *, context_lines: int = 0) -> Box:
    """The line's bounding rectangle plus a margin of 15% of its height, kept inside the page. The context crop adds one line above and below."""
    h = box.height
    m = round(h * margin_ratio)
    extra = round(h * 1.0 * context_lines)
    return Box(x0=max(0, box.x0 - m), y0=max(0, box.y0 - m - extra), x1=min(page_w, box.x1 + m), y1=min(page_h, box.y1 + m + extra))


def _crop_png(page: Image.Image, b: Box) -> bytes:
    out = io.BytesIO()
    page.crop((b.x0, b.y0, b.x1, b.y1)).save(out, "PNG")
    return out.getvalue()


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, PageOcrRequested)
    dossier_id, rev = revision_of(env)
    pref = keys.PageRef.parse(env.subject)
    dept = keys.department_of(dossier_id)
    tun = ctx.settings.tuning
    if ctx.ops.get_page(dossier_id, rev, pref.page_no).status in PAGE_FINAL:
        return  # a failed or finished page stays that way

    png = ctx.blobs.read("extracted", pref.dir + "page.png")
    page_sha = hashlib.sha256(png).hexdigest()
    ocr_path = pref.dir + "ocr.json"
    if ctx.blobs.exists("extracted", ocr_path):  # model outputs are written once: a retry reuses them and never pays twice
        ocr = read_model(ctx.blobs, "extracted", ocr_path, OcrResult)
    else:
        pdf = ctx.blobs.read("extracted", pref.dir + "page.pdf") if req.text_layer else None
        ocr = ctx.ocr.read(png, page_key=pref.key, text_layer_pdf=pdf)
        try:
            write_model(ctx.blobs, "extracted", ocr_path, ocr, once=True)
        except AlreadyExists:
            ocr = read_model(ctx.blobs, "extracted", ocr_path, OcrResult)

    page_img = Image.open(io.BytesIO(png)).convert("L")
    lines: list[TriageLine] = []
    for ln in ocr.lines:
        # Every handwritten line is second-read; a printed line only when its confidence is low. Text-layer lines never are.
        flagged = not ln.from_text_layer and (ln.style == "handwritten" or ln.conf < tun.printed_second_read_below)
        t = TriageLine(id=ln.id, style=ln.style, conf=ln.conf, route="second_read" if flagged else "accept", lang=ln.lang)
        if flagged:
            cb = crop_box(ln.box, ocr.page_width, ocr.page_height, tun.crop_margin_ratio)
            cropped = _crop_png(page_img, cb)
            ctx.blobs.write("extracted", f"{pref.dir}crops/{ln.id}.png", cropped, overwrite=True)
            ctx.blobs.write("extracted", f"{pref.dir}crops/{ln.id}.ctx.png",
                            _crop_png(page_img, crop_box(ln.box, ocr.page_width, ocr.page_height, tun.crop_margin_ratio, context_lines=1)), overwrite=True)
            t.crop, t.crop_box, t.crop_sha256 = f"crops/{ln.id}.png", cb, hashlib.sha256(cropped).hexdigest()
        lines.append(t)
    triage = Triage(page=pref.key, page_image_sha256=page_sha, lines=lines)
    write_model(ctx.blobs, "extracted", pref.dir + "triage.json", triage)

    flagged = triage.flagged()
    ctx.ops.set_page_status(dossier_id, rev, pref.page_no, PageStatus.awaiting_second_read if flagged else PageStatus.ocr_done, flagged_lines=len(flagged))
    if flagged:
        send(ctx, envelope("page.second-read.requested", pref.key, department=dept, dossier_id=dossier_id, revision=rev, payload={
            "page_no": pref.page_no, "page_dir": pref.dir, "page_image_sha256": page_sha,
            "lines": [{"line_id": t.id, "crop": t.crop, "lang_hint": t.lang} for t in flagged]}),  # deliberately no OCR text
             message_id=messageids.message_id("second-read", pref.key))
    else:
        send(ctx, envelope("page.reconcile.requested", pref.key, department=dept, dossier_id=dossier_id, revision=rev,
                           payload={"page_no": pref.page_no, "page_dir": pref.dir, "second_reads": {}, "expected_second_reads": 0}),
             message_id=messageids.message_id("reconcile", pref.key))


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
