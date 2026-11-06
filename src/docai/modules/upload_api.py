"""app-upload-api, service layer: opens an upload, accepts blocks, completes it (spec, Workflow 9, Steps 1 to 3).

Files land in `staging`, a container that is not immutable, and enter `raw` only after job-upload-commit has passed every
check. No storage address ever reaches the browser: the API writes with its own identity."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from docai.contracts import keys, messageids
from docai.contracts.enums import Capability, UploadMode, UploadStatus
from docai.runtime.context import Context
from docai.runtime.http import make_principal_dep, new_app
from docai.runtime.messaging import envelope, send
from docai.security.access import Principal, is_admin, require

_SHA = re.compile(r"^[0-9a-f]{64}$")
_SAFE_NAME = re.compile(r"^[^/\\\x00]{1,200}$")


class UploadError(Exception):
    pass


@dataclass
class Summary:
    upload_id: str
    department: str
    mode: str
    dossier_id: str | None
    files: list[dict]
    decisive_line: str
    block_bytes: int


def _block_bytes(ctx: Context) -> int:
    return ctx.settings.tuning.upload_block_kb * 1024


def _own(ctx: Context, p: Principal, upload_id: str) -> dict:
    up = ctx.ops.get_upload(upload_id)
    if up["uploaded_by_oid"] != p.oid and not is_admin(p):
        raise PermissionError("this upload belongs to someone else")
    return up


def open_upload(ctx: Context, p: Principal, *, department: str, 
                mode: UploadMode, dossier_id: str | None, files: list[dict]) -> Summary:
    """Checks, in this order: the capability, the dossier ID, then every file's name, type and size."""
    require(ctx.ops.registered_groups(), p, Capability.upload, department)
    tun = ctx.settings.tuning
    if mode is UploadMode.dossier:
        if not dossier_id or not keys.DOSSIER_ID_RE.match(dossier_id) or keys.department_of(dossier_id) != department:
            raise UploadError(f"the dossier ID must have the shape of a barcode and start with {department}")
    elif dossier_id:
        raise UploadError("bulk mode generates the dossier IDs: leave the dossier ID empty")
    if not files:
        raise UploadError("no files")
    seen: set[str] = set()
    for f in files:
        name = f.get("name", "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if not _SAFE_NAME.match(name) or name in seen or name == "dossier.json":
            raise UploadError(f"unusable file name: {name!r}")
        seen.add(name)
        if ext not in tun.upload_allowed_types:
            raise UploadError(f"unsupported_type: {name}")  # spreadsheets are refused here in the MVP
        if not 0 < f.get("bytes", 0) <= tun.upload_max_file_mb * 1024 * 1024:
            raise UploadError(f"{name} is empty or larger than {tun.upload_max_file_mb} MB")
        if not _SHA.match(f.get("sha256", "")):
            raise UploadError(f"{name}: sha256 must be 64 lowercase hex characters")
    uid = ctx.ops.create_upload(department=department, mode=mode.value, dossier_id=dossier_id, uploaded_by_oid=p.oid, uploaded_by_name=p.name,
                                files=files, block_bytes=_block_bytes(ctx))
    if mode is UploadMode.bulk:
        line = "Bulk upload: the files are grouped into new unfiled dossiers (UNF-…); a steward files them under a barcode later"
    else:
        latest = ctx.ops.latest_revision(dossier_id)  # type: ignore[arg-type]
        line = "This dossier does not exist yet" if latest == 0 else f"This dossier exists: your files will replace it as revision {latest + 1}"
    return Summary(uid, department, mode.value, dossier_id, files, line, _block_bytes(ctx))


def put_block(ctx: Context, p: Principal, upload_id: str, file_name: str, block_no: int, data: bytes) -> None:
    up = _own(ctx, p, upload_id)
    if up["status"] != UploadStatus.open.value:
        raise UploadError(f"the upload is {up['status']}")
    f = next((x for x in up["files"] if x["name"] == file_name), None)
    if f is None or not 0 <= block_no < f["blocks_total"]:
        raise UploadError("unknown file or block number")
    if len(data) > _block_bytes(ctx):
        raise UploadError("block too large")
    ctx.blobs.write_block("staging", f"{upload_id}/{file_name}", block_no, data)
    ctx.ops.touch_upload(upload_id)


def status(ctx: Context, p: Principal, upload_id: str) -> dict:
    """What the upload page asks to resume: the blocks the server holds. After commit, the status of the dossiers it became."""
    up = _own(ctx, p, upload_id)
    files = [{"name": f["name"], "blocks_total": f["blocks_total"], "blocks_held": ctx.blobs.list_blocks("staging", f"{upload_id}/{f['name']}")}
             for f in up["files"]]
    out = {"upload_id": upload_id, "status": up["status"], "reject_reason": up["reject_reason"], "files": files, "dossiers": []}
    for d in ctx.ops.upload_dossiers(upload_id):
        out["dossiers"].append({"dossier_id": d["dossier_id"], "revision": d["revision"], "status": _dossier_status(ctx, d)})
    return out


def _dossier_status(ctx: Context, d: dict) -> str:
    try:
        return ctx.ops.get_dossier(d["dossier_id"], d["revision"]).status
    except KeyError:
        return "committed"  # in raw; intake has not registered it yet


def complete(ctx: Context, p: Principal, upload_id: str) -> None:
    """Checks that every file is fully present with the declared size, then hands over to the commit job."""
    up = _own(ctx, p, upload_id)
    if up["status"] != UploadStatus.open.value:
        raise UploadError(f"the upload is already {up['status']}")
    for f in up["files"]:
        path = f"{upload_id}/{f['name']}"
        held = ctx.blobs.list_blocks("staging", path)
        if held != list(range(f["blocks_total"])):
            raise UploadError(f"{f['name']} is incomplete: {f['blocks_total'] - len(held)} block(s) missing")
        size = ctx.blobs.commit_blocks("staging", path, f["blocks_total"])
        if size != f["bytes"]:
            raise UploadError(f"{f['name']} has {size} bytes, not the declared {f['bytes']}")
    ctx.ops.set_upload_status(upload_id, UploadStatus.scanning.value)
    send(ctx, envelope("upload.commit.requested", upload_id, department=up["department"], payload={"upload_id": upload_id, "attempt": 1}),
         message_id=messageids.message_id("upload", upload_id))


class OpenRequest(BaseModel):
    department: str
    mode: UploadMode
    dossier_id: str | None = None
    files: list[dict]


def create_app(ctx: Context):
    app, principal = new_app("app-upload-api"), make_principal_dep(ctx)

    def bad(e: UploadError):
        return HTTPException(422, str(e))

    @app.post("/api/uploads")
    def open_(req: OpenRequest, p: Principal = Depends(principal)):
        try:
            return asdict(open_upload(ctx, p, department=req.department, mode=req.mode, dossier_id=req.dossier_id, files=req.files))
        except UploadError as e:
            raise bad(e) from e

    @app.put("/api/uploads/{upload_id}/files/{name}/blocks/{n}")
    async def block(upload_id: str, name: str, n: int, request: Request, p: Principal = Depends(principal)):
        try:
            put_block(ctx, p, upload_id, name, n, await request.body())
        except UploadError as e:
            raise bad(e) from e
        return {"ok": True}

    @app.get("/api/uploads/{upload_id}")
    def get(upload_id: str, p: Principal = Depends(principal)):
        return status(ctx, p, upload_id)

    @app.post("/api/uploads/{upload_id}/complete")
    def done(upload_id: str, p: Principal = Depends(principal)):
        try:
            complete(ctx, p, upload_id)
        except UploadError as e:
            raise bad(e) from e
        return {"ok": True}

    return app


if __name__ == "__main__":
    from docai.runtime.launch import http_app

    http_app(create_app)
