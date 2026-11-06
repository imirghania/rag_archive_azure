"""job-digital: converts a Word or text file to PDF with a text layer (spec, Workflow 3, Path A). The PDF then joins the
scan path, but its lines come from the text layer and carry the tier `digital_source`."""
from __future__ import annotations

import pypdfium2 as pdfium

from docai.contracts import keys, messageids
from docai.contracts.messages import ConvertRequested, Envelope, parse_payload
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, revision_of, send


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, ConvertRequested)
    dossier_id, rev = revision_of(env)
    dept = keys.department_of(dossier_id)
    dkey = keys.dossier_key(dossier_id, rev)
    out = f"{keys.extracted_dossier_dir(dossier_id, rev)}converted/{req.name}.pdf"
    try:
        pdf = ctx.converter.to_pdf(ctx.blobs.read("raw", req.raw_dir + req.name), req.name)
        pages = len(pdfium.PdfDocument(pdf))
        ctx.blobs.write("extracted", out, pdf, overwrite=True)  # deterministic: a retry writes the same file
        remaining = ctx.ops.finish_file(dossier_id, rev, req.name, "ready", pages=pages, converted_to=out)
    except FileNotFoundError:
        raise  # not there yet: the message is retried
    except Exception as e:  # noqa: BLE001 - a file that cannot be converted fails that file, not the dossier
        remaining = ctx.ops.finish_file(dossier_id, rev, req.name, "failed", reason=f"conversion_failed: {e}"[:200])
    if remaining == 0:  # fan-in on files: the last conversion starts preprocessing, so page numbers run through every file
        files = [f for f in ctx.ops.list_files(dossier_id, rev) if f.status != "failed"]
        if not files:
            ctx.ops.set_dossier_status(dossier_id, rev, "failed", "no file could be prepared")
            return
        send(ctx, envelope("dossier.preprocess.requested", dkey, department=dept, dossier_id=dossier_id, revision=rev,
                        payload={"files": [{"name": f.name, "location": f.location} for f in files], "raw_dir": req.raw_dir}),
            message_id=messageids.message_id("preprocess", dkey))


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
