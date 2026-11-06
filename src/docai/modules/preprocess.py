"""job-preprocess: turns files into clean 300 dpi page images (spec, Workflow 1, Step 3)."""
from __future__ import annotations

import hashlib
import io

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageFilter

from docai.contracts import keys, messageids
from docai.contracts.artifacts import Box, Line, LinesFile, PreprocessInfo
from docai.contracts.enums import TrustTier
from docai.contracts.messages import Envelope, PreprocessRequested, parse_payload
from docai.documents.artifactio import write_model
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send

TARGET_DPI = 300
PLACEHOLDER = "[page unreadable: {reason}]"


def deskew_angle(img: Image.Image, limit: float = 3.0, step: float = 0.25) -> float:
    """Projection-profile search on a small copy: the angle whose row sums vary the most is the text's own."""
    small = img.copy()
    small.thumbnail((600, 600))
    a = 255 - np.asarray(small.convert("L"), dtype=np.float32)
    if a.sum() == 0:
        return 0.0
    best, best_score = 0.0, -1.0
    for ang in np.arange(-limit, limit + step, step):
        r = np.asarray(Image.fromarray(a.astype(np.uint8)).rotate(float(ang), resample=Image.BILINEAR), dtype=np.float32)
        score = float(np.var(r.sum(axis=1)))
        if score > best_score:
            best, best_score = float(ang), score
    return best


def clean(img: Image.Image, dpi: int) -> tuple[Image.Image, float]:
    g = img.convert("L")
    if dpi and abs(dpi - TARGET_DPI) > 5:
        f = TARGET_DPI / dpi
        g = g.resize((round(g.width * f), round(g.height * f)), Image.LANCZOS)
    angle = deskew_angle(g)
    if abs(angle) >= 0.25:
        g = g.rotate(angle, resample=Image.BICUBIC, fillcolor=255, expand=False)
    return g.filter(ImageFilter.MedianFilter(3)), angle  # removes speckle noise


def _png(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, "PNG", dpi=(TARGET_DPI, TARGET_DPI))
    return b.getvalue()


def _frames(name: str, data: bytes):
    """Yields (frame_no, image-or-exception, dpi, text_layer, page_pdf_bytes) per page of a file, counting first."""
    if name.lower().endswith(".pdf"):
        pdf = pdfium.PdfDocument(data)
        n = len(pdf)
        yield n
        for i in range(n):
            page = pdf[i]
            try:
                text = page.get_textpage().get_text_range().strip()
                img = page.render(scale=TARGET_DPI / 72).to_pil()
                one = None
                if text:
                    out = pdfium.PdfDocument.new()
                    out.import_pages(pdf, [i])
                    buf = io.BytesIO()
                    out.save(buf)
                    one = buf.getvalue()
                yield i + 1, img, TARGET_DPI, bool(text), one
            except Exception as e:  # noqa: BLE001
                yield i + 1, e, TARGET_DPI, False, None
    else:
        im = Image.open(io.BytesIO(data))
        n = getattr(im, "n_frames", 1)
        yield n
        for i in range(n):
            try:
                im.seek(i)
                im.load()
                dpi = int(im.info.get("dpi", (TARGET_DPI, TARGET_DPI))[0] or TARGET_DPI)
                yield i + 1, im.copy(), dpi, False, None
            except Exception as e:  # noqa: BLE001 - a damaged frame fails one page, not the dossier
                yield i + 1, e, TARGET_DPI, False, None


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, PreprocessRequested)
    dossier_id, rev = revision_of(env)
    dept = keys.department_of(dossier_id)
    manifest_files = {f.name: f for f in ctx.ops.list_files(dossier_id, rev)}

    # 1. count every file first, so page numbers run through the whole dossier
    sources = []
    for ref in sorted(req.files, key=lambda f: manifest_files[f.name].seq):
        row = manifest_files[ref.name]
        container, path = ("raw", req.raw_dir + ref.name) if row.location == "raw" else ("extracted", f"{keys.extracted_dossier_dir(dossier_id, rev)}converted/{ref.name}.pdf")
        data = ctx.blobs.read(container, path)
        gen = _frames(path, data)  # the converted PDF of a Word file is read as a PDF
        n = next(gen)
        if row.pages is not None and row.pages != n:
            ctx.ops.set_dossier_status(dossier_id, rev, "failed_intake", f"page_count_mismatch: {ref.name} lists {row.pages}, has {n}")
            return  # held for a person
        sources.append((ref.name, gen, n))

    # 2. render every page (deterministic: a retry writes identical files), recording damaged frames
    pages, page_no, rendered = [], 0, []
    for name, gen, n in sources:
        for frame_no, img, dpi, text_layer, one_pdf in gen:
            page_no += 1
            pref = keys.PageRef(dossier_id, rev, page_no)
            if isinstance(img, Exception):
                pages.append({"page_no": page_no, "source_file": name, "frame": frame_no, "failed": True, "reason": "corrupt_image", "text_layer": False})
                rendered.append(("failed", pref, None))
                continue
            cleaned, angle = clean(img, dpi)
            png = _png(cleaned)
            info = PreprocessInfo(source=name, frame=frame_no, deskew_deg=round(angle, 2), dpi=TARGET_DPI, text_layer=text_layer,
                                  width=cleaned.width, height=cleaned.height, page_image_sha256=hashlib.sha256(png).hexdigest())
            ctx.blobs.write("extracted", pref.dir + "page.png", png, overwrite=True)
            write_model(ctx.blobs, "extracted", pref.dir + "preprocess.json", info)
            if one_pdf:
                ctx.blobs.write("extracted", pref.dir + "page.pdf", one_pdf, overwrite=True)
            pages.append({"page_no": page_no, "source_file": name, "frame": frame_no, "text_layer": text_layer})
            rendered.append(("ok", pref, text_layer))

    # 3. all page rows and total_pages in ONE transaction, before the first page message is sent
    ctx.ops.register_pages(dossier_id, rev, pages)  # None on a retry: the rows are already there
    for status, pref, _ in rendered:
        if status == "failed":  # the placeholder keeps page numbers aligned and makes the gap visible (tier `missing`)
            ph = Line(id="L1", text=PLACEHOLDER.format(reason="corrupt_image"), tier=TrustTier.missing, style="printed",
                      box=Box(x0=0, y0=0, x1=1, y1=1), source="placeholder")
            write_model(ctx.blobs, "extracted", pref.dir + "lines.v1.json", LinesFile(page_key=pref.key, page_no=pref.page_no, lines=[ph]))
            ctx.blobs.write("extracted", pref.dir + "page.v1.md", (ph.text + "\n").encode(), overwrite=True)
    d = ctx.ops.get_dossier(dossier_id, rev)
    if d.pages_failed == d.total_pages:
        ctx.ops.set_dossier_status(dossier_id, rev, "failed", "every page failed")
        return

    # 4. fan-out
    for status, pref, text_layer in rendered:
        if status == "ok":
            send(ctx, envelope("page.ocr.requested", pref.key, department=dept, dossier_id=dossier_id, revision=rev,
                               payload={"page_no": pref.page_no, "page_dir": pref.dir, "image": "page.png", "text_layer": bool(text_layer)}),
                 message_id=messageids.message_id("ocr", pref.key))


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
