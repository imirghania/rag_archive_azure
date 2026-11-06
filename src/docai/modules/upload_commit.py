"""job-upload-commit: checks an upload and commits it to `raw` (spec, Workflow 9, Step 4).

Retry-safe: a crash can happen between any two moves. Every write to `raw` is write-once; a file that already exists with
the right hash counts as copied, one with a different hash stops the job (`raw_conflict`) because `raw` can never be
overwritten. `dossier.json` is written last, and the intake message is sent once per dossier."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import timedelta

import pypdfium2 as pdfium
from PIL import Image

from docai.contracts import keys, messageids
from docai.contracts.artifacts import Manifest, ManifestFile
from docai.contracts.enums import UploadMode, UploadStatus
from docai.contracts.messages import Envelope, UploadCommitRequested, parse_payload
from docai.runtime.context import Context
from docai.runtime.messaging import DeadLetter, envelope, send

MAGIC = {"pdf": (b"%PDF-",), "tif": (b"II*\x00", b"MM\x00*"), "tiff": (b"II*\x00", b"MM\x00*"), "docx": (b"PK\x03\x04",), "doc": (b"\xd0\xcf\x11\xe0",)}


class Rejected(Exception):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


@dataclass
class Checked:
    name: str
    bytes: int
    sha256: str
    pages: int | None


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower()


def _check_file(name: str, data: bytes, declared_sha: str, max_pages: int) -> Checked:
    ext = _ext(name)
    sha = hashlib.sha256(data).hexdigest()
    if sha != declared_sha:  # integrity
        raise Rejected("integrity", f"{name} does not match the hash the browser computed")
    if ext in MAGIC and not any(data.startswith(m) for m in MAGIC[ext]):
        raise Rejected("integrity", f"{name} is not a real .{ext} file")
    if ext == "txt" and b"\x00" in data[:4096]:
        raise Rejected("integrity", f"{name} is not a text file")
    pages: int | None = None
    if ext == "pdf":  # safe content: not encrypted; pages counted here and written into the manifest
        try:
            pages = len(pdfium.PdfDocument(data))
        except pdfium.PdfiumError as e:
            raise Rejected("unsafe_content", f"{name} cannot be opened (encrypted or damaged): {e}") from e
    elif ext in ("tif", "tiff"):
        try:
            pages = getattr(Image.open(io.BytesIO(data)), "n_frames", 1)
        except Exception as e:  # noqa: BLE001
            raise Rejected("unsafe_content", f"{name} cannot be read: {e}") from e
    elif ext == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = z.namelist()
                if "word/document.xml" not in names or any(n.lower().endswith("vbaproject.bin") for n in names):
                    raise Rejected("unsafe_content", f"{name} is macro-enabled or not a Word document")
        except zipfile.BadZipFile as e:
            raise Rejected("unsafe_content", f"{name} is damaged or password protected") from e
    if pages is not None and pages > max_pages:
        raise Rejected("too_many_pages", f"{name} has {pages} pages; the limit is {max_pages}")
    return Checked(name, len(data), sha, pages)


def _groups(files: list[Checked], max_files: int, max_pages: int) -> list[list[Checked]]:
    """Bulk mode: file-name order, at most `max_files` files or `max_pages` pages per dossier."""
    out: list[list[Checked]] = []
    pages = 0
    for f in sorted(files, key=lambda x: x.name):
        if not out or len(out[-1]) >= max_files or pages + (f.pages or 0) > max_pages:
            out.append([])
            pages = 0
        out[-1].append(f)
        pages += f.pages or 0
    return out


def handle(ctx: Context, env: Envelope) -> None:
    req = parse_payload(env)
    assert isinstance(req, UploadCommitRequested)
    up = ctx.ops.get_upload(req.upload_id)
    if up["status"] in (UploadStatus.rejected.value, UploadStatus.expired.value):
        return
    if up["status"] == UploadStatus.committed.value:  # a retry after a crash between the commit and the intake messages
        _send_intake(ctx, up)
        return
    try:
        _scan(ctx, up, req)
        if up.get("_pending"):
            return  # a copy of this message is scheduled; this one is completed
        checked = _check_all(ctx, up)
        _commit(ctx, up, checked)
    except Rejected as r:
        _reject(ctx, up, r.reason, r.detail, quarantine=r.reason == "malware")
    else:
        _send_intake(ctx, ctx.ops.get_upload(req.upload_id))


def _staging(up: dict, name: str) -> str:
    return f"{up['upload_id']}/{name}"


def _scan(ctx: Context, up: dict, req: UploadCommitRequested) -> None:
    """The place of the malware check. In stub mode it reports every file clean. With Defender, a file without a result
    yet makes the job reschedule itself 60 seconds later with a new MessageId (the same one would be dropped as a duplicate)."""
    tun = ctx.settings.tuning
    if tun.upload_scan_mode == "stub":
        return
    results = {f["name"]: ctx.blobs.scan_result("staging", _staging(up, f["name"])) for f in up["files"]}
    if "malicious" in results.values():  # the whole upload, not just that file: a dossier with a missing file would look complete
        raise Rejected("malware", ", ".join(n for n, r in results.items() if r == "malicious"))
    if "pending" in results.values():
        up["_pending"] = True
        if req.attempt >= tun.upload_scan_max_attempts:
            raise DeadLetter("scan_timeout")
        nxt = req.attempt + 1
        ctx.queue.send("q-upload-commit", envelope("upload.commit.requested", up["upload_id"], department=up["department"],
                                                   payload={"upload_id": up["upload_id"], "attempt": nxt}),
                       message_id=messageids.retry_try(messageids.message_id("upload", up["upload_id"]), nxt),
                       scheduled_at=ctx.clock.now() + timedelta(seconds=tun.upload_scan_retry_seconds))


def _check_all(ctx: Context, up: dict) -> list[Checked]:
    return [_check_file(f["name"], ctx.blobs.read("staging", _staging(up, f["name"])), f["sha256"], ctx.settings.tuning.upload_max_pages) for f in up["files"]]


def _plan(ctx: Context, up: dict, files: list[Checked]) -> list[tuple[str, int, list[Checked]]]:
    """(dossier ID, revision, files) per dossier this upload becomes."""
    tun = ctx.settings.tuning
    if up["mode"] == UploadMode.dossier.value:
        dossier = up["dossier_id"]
        existing = ctx.ops.upload_dossiers(up["upload_id"])
        latest = ctx.ops.latest_revision(dossier)
        rev = existing[0]["revision"] if existing else latest + 1
        if latest and not existing:  # duplicate: the same set of files as the dossier's latest revision
            old = {(f.name, f.sha256) for f in ctx.ops.list_files(dossier, latest)}
            if old == {(c.name, c.sha256) for c in files}:
                raise Rejected("duplicate_upload", f"identical to revision {latest} of {dossier}")
        return [(dossier, rev, files)]
    groups = _groups(files, tun.bulk_max_files, tun.bulk_max_pages)
    existing = ctx.ops.upload_dossiers(up["upload_id"])
    if len(existing) == len(groups):  # a retry: the IDs were already assigned
        ids = [e["dossier_id"] for e in existing]
    else:
        day = ctx.clock.now().strftime("%Y%m%d")
        ids = [f"UNF-{up['department']}-{day}-{ctx.ops.next_unfiled_seq():04d}" for _ in groups]
    return [(i, 1, g) for i, g in zip(ids, groups, strict=True)]


def _manifest_bytes(up: dict, dossier: str, files: list[Checked]) -> bytes:
    m = Manifest(dossier_id=dossier, source="upload", upload_id=up["upload_id"], uploaded_by=up["uploaded_by_oid"], segmentation="auto",
                 files=[ManifestFile(name=f.name, bytes=f.bytes, sha256=f.sha256, pages=f.pages) for f in sorted(files, key=lambda x: x.name)])
    return (json.dumps(json.loads(m.model_dump_json(by_alias=True)), indent=1, sort_keys=True) + "\n").encode()


def _commit(ctx: Context, up: dict, files: list[Checked]) -> None:
    plan = _plan(ctx, up, files)
    by_name = {f.name: f for f in files}
    for dossier, rev, group in plan:
        base = keys.raw_dossier_dir(dossier, rev)
        manifest = _manifest_bytes(up, dossier, group)
        ctx.ops.add_upload_dossier(up["upload_id"], dossier, rev, hashlib.sha256(manifest).hexdigest())
        for f in group:
            _put_once(ctx, up, f"{base}{f.name}", lambda f=f: ctx.blobs.copy("staging", _staging(up, f.name), "raw", f"{base}{f.name}"), by_name[f.name].sha256)
        _put_once(ctx, up, f"{base}dossier.json", lambda m=manifest: ctx.blobs.write("raw", f"{base}dossier.json", m), hashlib.sha256(manifest).hexdigest())  # last
    ctx.ops.set_upload_status(up["upload_id"], UploadStatus.committed.value)


def _put_once(ctx: Context, up: dict, path: str, write, expected_sha: str) -> None:
    """Write-once with retry safety: an existing file with the right hash counts as copied; a different one is a conflict."""
    if ctx.blobs.exists("raw", path):
        if hashlib.sha256(ctx.blobs.read("raw", path)).hexdigest() != expected_sha:
            raise Rejected("raw_conflict", f"{path} already exists with different content")
        return
    write()
    if hashlib.sha256(ctx.blobs.read("raw", path)).hexdigest() != expected_sha:
        ctx.blobs.delete("raw", path)
        raise Rejected("integrity", f"the copy of {path} does not match the hash")


def _send_intake(ctx: Context, up: dict) -> None:
    for d in ctx.ops.upload_dossiers(up["upload_id"]):
        if d["intake_sent"]:
            continue
        base = keys.raw_dossier_dir(d["dossier_id"], d["revision"])
        env = envelope("dossier.received", d["dossier_id"], department=up["department"], dossier_id=d["dossier_id"],
                       payload={"manifest": base + "dossier.json", "manifest_hash": d["manifest_hash"], "source": "upload", "upload_id": up["upload_id"]})
        send(ctx, env, message_id=messageids.intake(d["dossier_id"], d["manifest_hash"]))  # a duplicate inside the window is dropped
        ctx.ops.mark_intake_sent(up["upload_id"], d["dossier_id"])


def _reject(ctx: Context, up: dict, reason: str, detail: str, *, quarantine: bool) -> None:
    if quarantine:  # the platform team investigates quarantined files
        for f in up["files"]:
            p = _staging(up, f["name"])
            ctx.blobs.copy("staging", p, "quarantine", p)
            ctx.blobs.delete("staging", p)
    ctx.ops.set_upload_status(up["upload_id"], UploadStatus.rejected.value, reason)
    send(ctx, envelope("upload.rejected", up["upload_id"], department=up["department"],
                       payload={"upload_id": up["upload_id"], "uploaded_by": up["uploaded_by_oid"], "reason": f"{reason}: {detail}" if detail else reason}),
         message_id=f"rejected:{up['upload_id']}")


if __name__ == "__main__":
    from docai.runtime.launch import queue_job

    queue_job(handle)
