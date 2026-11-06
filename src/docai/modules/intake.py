"""job-intake: verifies a committed dossier and registers a revision (spec, Workflow 1, Step 2)."""
from __future__ import annotations

import hashlib
import json

from docai.contracts import keys, messageids
from docai.contracts.artifacts import Manifest
from docai.contracts.messages import (
    DossierReceived,
    Envelope,
    ReprocessRequested,
    parse_payload,
)
from docai.runtime.context import Context
from docai.runtime.messaging import envelope, send

SCAN_TYPES = {"tif": "tiff", "tiff": "tiff", "pdf": "pdf"}
DIGITAL_TYPES = {"doc": "doc", "docx": "docx", "txt": "txt"}


class IntakeError(Exception):
    pass


def _classify(name: str) -> tuple[str, str]:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in SCAN_TYPES:
        return SCAN_TYPES[ext], "scan"
    if ext in DIGITAL_TYPES:
        return DIGITAL_TYPES[ext], "digital"
    raise IntakeError(f"unsupported_type: {name}")  # spreadsheets are refused (spec, Path B deferred)


def handle(ctx: Context, env: Envelope) -> None:
    payload = parse_payload(env)
    dossier_id = env.dossier_id or ""
    department = keys.department_of(dossier_id)

    if env.type == "dossier.reprocess.requested":
        assert isinstance(payload, ReprocessRequested)
        # the revision whose manifest is reused is the one being reprocessed; its folder holds the files
        raw_dir = _raw_dir_for(ctx, dossier_id, payload.from_revision)
        manifest_path = raw_dir + "dossier.json"
        source, from_revision, upload_id = "reprocess", payload.from_revision, None
    else:
        assert isinstance(payload, DossierReceived)
        manifest_path = payload.manifest
        raw_dir = manifest_path.rsplit("dossier.json", 1)[0]
        source, from_revision, upload_id = "upload", None, payload.upload_id

    raw_manifest = ctx.blobs.read("raw", manifest_path)
    manifest = Manifest.model_validate(json.loads(raw_manifest))
    manifest_hash = hashlib.sha256(raw_manifest).hexdigest()

    files = []
    for seq, f in enumerate(manifest.files, start=1):
        ftype, route = _classify(f.name)
        data = ctx.blobs.read("raw", raw_dir + f.name)  # missing file: FileNotFoundError, the message is retried
        if len(data) != f.bytes or hashlib.sha256(data).hexdigest() != f.sha256:
            raise IntakeError(f"integrity: {f.name} does not match the manifest")
        files.append({"name": f.name, "seq": seq, "type": ftype, "route": route, "bytes": f.bytes, "sha256": f.sha256, "pages": f.pages})

    expected = sum(f["pages"] or 0 for f in files) or None
    res = ctx.ops.register_dossier(dossier_id=dossier_id, department=department, manifest_path=manifest_path,
                                   manifest_hash=manifest_hash, files=files, source=source, from_revision=from_revision,
                                   upload_id=upload_id, segmentation=manifest.segmentation, expected_pages=expected)
    if res.status != "registered":
        return  # a duplicate manifest, or a stale reprocess: completed without work

    rev, key = res.revision, keys.dossier_key(dossier_id, res.revision)
    if res.files_to_prepare == 0:
        send(ctx, envelope("dossier.preprocess.requested", key, department=department, dossier_id=dossier_id, revision=rev,
                           payload={"files": [{"name": f["name"], "location": "raw"} for f in files], "raw_dir": raw_dir}),
             message_id=messageids.message_id("preprocess", key))
    else:
        for f in files:
            if f["route"] == "digital":
                send(ctx, envelope("file.convert.requested", f"{key}/{f['name']}", department=department, dossier_id=dossier_id,
                                   revision=rev, payload={"name": f["name"], "raw_dir": raw_dir}),
                     message_id=messageids.message_id("convert", f"{key}/{f['name']}"))


def _raw_dir_for(ctx: Context, dossier_id: str, revision: int) -> str:
    """The folder that holds the manifest of `revision`: the dossier folder for r1, an rN subfolder for a rescan."""
    d = ctx.ops.get_dossier(dossier_id, revision)
    return d.manifest_path.rsplit("dossier.json", 1)[0]


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
