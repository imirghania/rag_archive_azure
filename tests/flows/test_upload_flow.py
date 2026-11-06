"""Workflow 9 and the Failures table on the local fakes: upload, scan, checks, commit, retries, bulk, conversion, watchdog."""
import hashlib
import io
import zipfile

import pytest

from docai.security.access import Principal
from docai.adapters.local.clock import FixedClock
from docai.adapters.local.convert import PurePdfConverter
from docai.contracts import keys
from docai.contracts.enums import TrustTier, UploadMode
from docai.contracts.artifacts import LinesFile
from docai.modules import chat_api, review, upload_api, watchdog
from docai.modules.upload_api import UploadError
from docai.runtime.runner import drain, load_handlers, process_queue

from conftest import FIN_EXPERTS, FIN_READERS, FIN_TREASURY

SARA = Principal("aaaaaaaa-0000-0000-0000-000000000001", "Sara Aziz", ["DocAI.Expert"], [FIN_READERS, FIN_EXPERTS, FIN_TREASURY])
LAYLA = Principal("aaaaaaaa-0000-0000-0000-00000000000a", "Layla", ["DocAI.Reader"], [FIN_READERS])
YOUSEF = Principal("aaaaaaaa-0000-0000-0000-000000000004", "Yousef", ["DocAI.Admin"], [])
LEASE, INVOICES = "FIN-C03-S2-F0117", "FIN-C05-S1-F0118"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def pump(ctx):
    for _ in range(10):
        if review.relay_outbox(ctx) + drain(ctx) == 0:
            return


def spec_of(name: str, data: bytes) -> dict:
    return {"name": name, "bytes": len(data), "sha256": sha(data)}


def do_upload(ctx, p, dossier_id, files: dict[str, bytes], *, mode=UploadMode.dossier, block=None, department="FIN", complete=True):
    """What the browser does: open, send blocks, press Complete."""
    s = upload_api.open_upload(ctx, p, department=department, mode=mode, dossier_id=dossier_id, files=[spec_of(n, d) for n, d in files.items()])
    size = s.block_bytes if block is None else block
    for name, data in files.items():
        for i in range(0, max(len(data), 1), size):
            upload_api.put_block(ctx, p, s.upload_id, name, i // size, data[i:i + size])
    if complete:
        upload_api.complete(ctx, p, s.upload_id)
    return s


def sample_files(ctx, dossier_id, names=None):
    d = ctx.samples / "dossiers" / dossier_id
    return {f.name: f.read_bytes() for f in sorted(d.iterdir()) if f.name != "dossier.json" and (names is None or f.name in names)}


def pdf(text="hello"):
    return PurePdfConverter().to_pdf(text.encode(), "x.txt")


@pytest.fixture
def small_blocks(ctx):
    ctx.settings.tuning.upload_block_kb = 64  # force several blocks per sample file
    return ctx


def test_an_upload_goes_from_blocks_in_staging_to_a_completed_dossier(small_blocks):
    ctx = small_blocks
    files = sample_files(ctx, LEASE)
    s = do_upload(ctx, SARA, LEASE, files)
    assert s.decisive_line == "This dossier does not exist yet"
    assert ctx.ops.get_upload(s.upload_id)["status"] == "scanning" and ctx.queue.depth("q-upload-commit") == 1
    pump(ctx)
    st = upload_api.status(ctx, SARA, s.upload_id)
    assert st["status"] == "committed" and st["dossiers"] == [{"dossier_id": LEASE, "revision": 1, "status": "completed"}]
    assert ctx.blobs.exists("raw", f"FIN/{LEASE}/dossier.json")
    assert [p for p in ctx.blobs.list("raw", f"FIN/{LEASE}/") if p.endswith(".tif")] == [f"FIN/{LEASE}/scan_001.tif", f"FIN/{LEASE}/scan_002.tif"]
    assert ctx.ops.get_dossier(LEASE, 1).total_pages == 5


def test_an_interrupted_upload_resumes_from_the_blocks_the_server_holds(small_blocks):
    ctx = small_blocks
    name, data = next(iter(sample_files(ctx, LEASE, ["scan_001.tif"]).items()))
    s = upload_api.open_upload(ctx, SARA, department="FIN", mode=UploadMode.dossier, dossier_id=LEASE, files=[spec_of(name, data)])
    bs = s.block_bytes
    upload_api.put_block(ctx, SARA, s.upload_id, name, 0, data[:bs])
    assert upload_api.status(ctx, SARA, s.upload_id)["files"][0]["blocks_held"] == [0]
    with pytest.raises(UploadError, match="incomplete"):
        upload_api.complete(ctx, SARA, s.upload_id)
    for i in range(1, -(-len(data) // bs)):
        upload_api.put_block(ctx, SARA, s.upload_id, name, i, data[i * bs:(i + 1) * bs])
    upload_api.complete(ctx, SARA, s.upload_id)
    with pytest.raises(UploadError, match="already"):
        upload_api.complete(ctx, SARA, s.upload_id)


def test_the_opening_checks_refuse_what_cannot_be_committed(ctx):
    ok = [spec_of("a.pdf", b"x")]
    def op(p=SARA, **kw):
        return upload_api.open_upload(ctx, p, **{"department": "FIN", "mode": UploadMode.dossier, "dossier_id": LEASE, "files": ok, **kw})
    with pytest.raises(PermissionError):
        op(LAYLA)  # a reader cannot upload
    with pytest.raises(PermissionError):
        op(YOUSEF)  # the admin role gives no content rights
    with pytest.raises(UploadError, match="barcode"):
        op(dossier_id="HR-C01-S1-F0010")  # wrong department for this ID
    with pytest.raises(UploadError, match="barcode"):
        op(dossier_id="not an id")
    with pytest.raises(UploadError, match="unsupported_type"):
        op(files=[spec_of("budget.xlsx", b"x")])  # spreadsheets are refused in the MVP
    with pytest.raises(UploadError, match="larger"):
        op(files=[{"name": "big.pdf", "bytes": 600 * 1024 * 1024, "sha256": "0" * 64}])
    with pytest.raises(UploadError, match="bulk"):
        op(mode=UploadMode.bulk)
    with pytest.raises(UploadError, match="unusable"):
        op(files=[spec_of("../evil.pdf", b"x")])
    with pytest.raises(PermissionError):
        op(department="HR", dossier_id="HR-C01-S1-F0010")  # Sara is no expert in HR


def test_only_the_owner_or_an_admin_can_touch_an_upload(ctx):
    s = do_upload(ctx, SARA, LEASE, {"a.pdf": pdf()}, complete=False)
    other = Principal("aaaaaaaa-0000-0000-0000-0000000000fe", "Other", ["DocAI.Expert"], [FIN_READERS, FIN_EXPERTS])
    with pytest.raises(PermissionError):
        upload_api.put_block(ctx, other, s.upload_id, "a.pdf", 0, b"x")
    assert upload_api.status(ctx, YOUSEF, s.upload_id)["status"] == "open"


@pytest.mark.parametrize("files,reason", [
    ({"a.pdf": b"%PDF-1.4 not really a pdf"}, "unsafe_content"),
    ({"a.pdf": b"MZ this is an executable"}, "integrity"),
    ({"a.docx": b"PK\x03\x04 not a word file"}, "unsafe_content"),
])
def test_content_checks_reject_the_whole_upload_with_a_reason_and_tell_the_uploader(ctx, files, reason):
    s = do_upload(ctx, SARA, LEASE, {"good.pdf": pdf(), **files})
    pump(ctx)
    up = ctx.ops.get_upload(s.upload_id)
    assert up["status"] == "rejected" and up["reject_reason"] == reason
    assert not ctx.blobs.list("raw"), "nothing reaches raw: the good file is not committed on its own"
    titles = [r["title"] for r in ctx.ops.inbox_for(SARA.oid, [], False)]
    assert any("was rejected" in t for t in titles) and ctx.ops.inbox_for(YOUSEF.oid, [], True)


def test_a_macro_enabled_word_file_is_refused(ctx):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w/>")
        z.writestr("word/vbaProject.bin", b"macro")
    s = do_upload(ctx, SARA, LEASE, {"m.docx": buf.getvalue()})
    pump(ctx)
    assert ctx.ops.get_upload(s.upload_id)["reject_reason"] == "unsafe_content"


def test_a_file_that_changed_after_the_browser_hashed_it_is_an_integrity_failure(ctx):
    data = pdf()
    s = upload_api.open_upload(ctx, SARA, department="FIN", mode=UploadMode.dossier, dossier_id=LEASE, files=[spec_of("a.pdf", data)])
    upload_api.put_block(ctx, SARA, s.upload_id, "a.pdf", 0, data[:-1] + b"X")  # same size, different content
    upload_api.complete(ctx, SARA, s.upload_id)
    pump(ctx)
    assert ctx.ops.get_upload(s.upload_id)["reject_reason"] == "integrity"


def test_too_many_pages_are_refused(ctx):
    ctx.settings.tuning.upload_max_pages = 2
    s = do_upload(ctx, SARA, LEASE, sample_files(ctx, LEASE, ["scan_001.tif"]))  # 3 pages
    pump(ctx)
    assert ctx.ops.get_upload(s.upload_id)["reject_reason"] == "too_many_pages"


def test_the_scan_is_a_stub_that_reports_every_file_clean(ctx):
    s = do_upload(ctx, SARA, LEASE, {"a.pdf": pdf("EICAR-STANDARD-ANTIVIRUS-TEST-FILE")})
    pump(ctx)
    assert ctx.ops.get_upload(s.upload_id)["status"] == "committed", "in stub mode the scan check passes everything"


def test_with_the_scan_on_malware_quarantines_the_whole_upload(ctx):
    ctx.settings.tuning.upload_scan_mode = "defender"
    s = do_upload(ctx, SARA, LEASE, {"good.pdf": pdf(), "bad.pdf": pdf("EICAR-STANDARD-ANTIVIRUS-TEST-FILE")})
    pump(ctx)
    up = ctx.ops.get_upload(s.upload_id)
    assert up["status"] == "rejected" and up["reject_reason"] == "malware"
    assert ctx.blobs.exists("quarantine", f"{s.upload_id}/good.pdf") and not ctx.blobs.exists("staging", f"{s.upload_id}/good.pdf")
    assert not ctx.blobs.list("raw")


def test_a_pending_scan_reschedules_itself_with_new_message_ids_and_then_gives_up(ctx):
    clock = FixedClock()
    ctx.ops.clock = ctx.queue._clock = ctx.clock = clock
    ctx.settings.tuning.upload_scan_mode = "defender"
    s = do_upload(ctx, SARA, LEASE, {"pending_scan.pdf": pdf()})
    h = load_handlers()["q-upload-commit"]
    process_queue(ctx, "q-upload-commit", h)
    assert ctx.ops.get_upload(s.upload_id)["status"] == "scanning"
    assert ("q-upload-commit", "upload.commit.requested", f"upload:{s.upload_id}:try2") in ctx.queue.sent_log
    assert process_queue(ctx, "q-upload-commit", h) == 0, "the copy is scheduled 60 seconds later, not now"
    clock.advance(seconds=61)
    process_queue(ctx, "q-upload-commit", h)
    assert (("q-upload-commit", "upload.commit.requested", f"upload:{s.upload_id}:try3") in ctx.queue.sent_log)
    ctx.blobs.finish_scan("staging", f"{s.upload_id}/pending_scan.pdf")  # the scan result arrives
    clock.advance(seconds=61)
    pump(ctx)
    assert ctx.ops.get_upload(s.upload_id)["status"] == "committed"


def test_a_scan_that_never_finishes_is_dead_lettered_as_scan_timeout(ctx):
    clock = FixedClock()
    ctx.ops.clock = ctx.queue._clock = ctx.clock = clock
    ctx.settings.tuning.upload_scan_mode = "defender"
    ctx.settings.tuning.upload_scan_max_attempts = 3
    do_upload(ctx, SARA, LEASE, {"pending_scan.pdf": pdf()})
    h = load_handlers()["q-upload-commit"]
    for _ in range(3):
        process_queue(ctx, "q-upload-commit", h)
        clock.advance(seconds=61)
    dead = ctx.queue.peek_dead_letters("q-upload-commit")
    assert dead and dead[0].message_id.endswith(":try3")


def test_the_same_files_again_are_a_duplicate_and_changed_files_become_the_next_revision(small_blocks):
    ctx = small_blocks
    files = sample_files(ctx, LEASE)
    do_upload(ctx, SARA, LEASE, files)
    pump(ctx)
    s2 = do_upload(ctx, SARA, LEASE, files)
    assert "revision 2" in upload_api.open_upload(ctx, SARA, department="FIN", mode=UploadMode.dossier, dossier_id=LEASE, files=[spec_of(n, d) for n, d in files.items()]).decisive_line
    pump(ctx)
    assert ctx.ops.get_upload(s2.upload_id)["reject_reason"] == "duplicate_upload" and ctx.ops.latest_revision(LEASE) == 1
    new = sample_files(ctx, "FIN-C07-S1-F0201", ["scan_001.tif"])  # a different scan of the same dossier
    s3 = do_upload(ctx, SARA, LEASE, {**{k: v for k, v in files.items() if k != "scan_002.tif"}, "scan_002.tif": new["scan_001.tif"]})
    pump(ctx)
    assert ctx.ops.get_upload(s3.upload_id)["status"] == "committed"
    assert ctx.blobs.exists("raw", f"FIN/{LEASE}/r2/dossier.json") and ctx.ops.latest_revision(LEASE) == 2


def test_a_crash_before_the_manifest_is_written_is_retried_without_a_conflict_in_write_once_raw(small_blocks):
    ctx = small_blocks
    s = do_upload(ctx, SARA, LEASE, sample_files(ctx, LEASE))
    real, calls = ctx.blobs.write, {"n": 0}

    def crash_once(container, path, data, **kw):
        if path.endswith("dossier.json") and calls["n"] == 0:
            calls["n"] += 1
            raise RuntimeError("the container died")
        return real(container, path, data, **kw)
    ctx.blobs.write = crash_once
    process_queue(ctx, "q-upload-commit", load_handlers()["q-upload-commit"])  # fails after the files were copied
    assert ctx.ops.get_upload(s.upload_id)["status"] == "scanning" and not ctx.blobs.exists("raw", f"FIN/{LEASE}/dossier.json")
    assert ctx.blobs.exists("raw", f"FIN/{LEASE}/scan_001.tif")
    ctx.blobs.write = real
    ctx.queue._entities["q-upload-commit"].live[0].locked = False  # the lock expires; the message comes back
    pump(ctx)
    assert ctx.ops.get_upload(s.upload_id)["status"] == "committed" and ctx.ops.get_dossier(LEASE, 1).status == "completed"


def test_a_different_file_already_in_raw_is_a_conflict_and_is_never_overwritten(ctx):
    ctx.blobs.write("raw", f"FIN/{LEASE}/a.pdf", b"someone else's original")
    s = do_upload(ctx, SARA, LEASE, {"a.pdf": pdf()})
    pump(ctx)
    up = ctx.ops.get_upload(s.upload_id)
    assert up["reject_reason"] == "raw_conflict" and ctx.blobs.read("raw", f"FIN/{LEASE}/a.pdf") == b"someone else's original"
    assert ctx.ops.inbox_for(YOUSEF.oid, [], True), "the platform team is alerted"


def test_the_intake_message_is_sent_once_even_if_the_commit_runs_again(ctx):
    s = do_upload(ctx, SARA, LEASE, {"a.pdf": pdf()})
    process_queue(ctx, "q-upload-commit", load_handlers()["q-upload-commit"])
    n = sum(1 for m in ctx.queue.sent_log if m[1] == "dossier.received")
    from docai.modules import upload_commit
    from docai.contracts.messages import Envelope
    env = Envelope(type="upload.commit.requested", subject=s.upload_id, department="FIN", payload={"upload_id": s.upload_id, "attempt": 1})
    upload_commit.handle(ctx, env)
    upload_commit.handle(ctx, env)
    assert sum(1 for m in ctx.queue.sent_log if m[1] == "dossier.received") == n == 1


def test_bulk_upload_groups_loose_files_into_unfiled_dossiers(ctx):
    ctx.settings.tuning.bulk_max_files = 2
    files = {f"doc_{i}.pdf": pdf(f"document number {i}") for i in range(5)}
    s = do_upload(ctx, SARA, None, files, mode=UploadMode.bulk)
    assert "unfiled" in s.decisive_line
    h = load_handlers()
    process_queue(ctx, "q-upload-commit", h["q-upload-commit"])
    ds = ctx.ops.upload_dossiers(s.upload_id)
    assert [d["dossier_id"].rsplit("-", 1)[1] for d in ds] == ["0001", "0002", "0003"]
    assert all(keys.DOSSIER_ID_RE.match(d["dossier_id"]) and d["dossier_id"].startswith("UNF-FIN-") for d in ds)
    import json
    m = [json.loads(ctx.blobs.read("raw", f"FIN/{d['dossier_id']}/dossier.json")) for d in ds]
    assert [[f["name"] for f in x["files"]] for x in m] == [["doc_0.pdf", "doc_1.pdf"], ["doc_2.pdf", "doc_3.pdf"], ["doc_4.pdf"]]
    assert {x["segmentation"] for x in m} == {"auto"} and ctx.queue.depth("q-intake") == 3


def test_word_and_text_files_are_converted_and_join_the_scan_path_as_digital_source(small_blocks):
    ctx = small_blocks
    files = sample_files(ctx, "FIN-C03-S2-F0118")  # invoice_batch.pdf (a scan), memo.docx, notes.txt
    do_upload(ctx, SARA, "FIN-C03-S2-F0118", files)  # the invoice batch has OCR fixtures under its own dossier ID
    pump(ctx)
    d = ctx.ops.get_dossier("FIN-C03-S2-F0118", 1)
    assert d.status == "completed" and d.total_pages == 4
    rows = {f.name: f for f in ctx.ops.list_files("FIN-C03-S2-F0118", 1)}
    assert rows["memo.docx"].status == "ready" and rows["memo.docx"].location == "extracted" and rows["memo.docx"].pages == 1
    docs = ctx.ops.list_documents("FIN-C03-S2-F0118", 1)
    assert len(docs) == 4, "each converted file is exactly one document and never merges with scanned pages"
    memo_page = keys.PageRef("FIN-C03-S2-F0118", 1, 3)
    lf = LinesFile.model_validate_json(ctx.blobs.read("extracted", memo_page.dir + "lines.v1.json"))
    assert {ln.tier for ln in lf.lines} == {TrustTier.digital_source}
    assert not ctx.vision.calls, "a text layer is never second-read"
    assert any("3.1M" in (ctx.search.get("docs", c) or {}).get("text_en", "") for c in ctx.search.ids("docs"))


def test_a_file_that_cannot_be_converted_fails_that_file_not_the_dossier(ctx):
    class Broken:
        def to_pdf(self, data, filename):
            raise RuntimeError("corrupt document")
    ctx.converter = Broken()
    files = sample_files(ctx, "FIN-C03-S2-F0118")
    do_upload(ctx, SARA, "FIN-C03-S2-F0118", files)
    pump(ctx)
    d = ctx.ops.get_dossier("FIN-C03-S2-F0118", 1)
    assert d.status == "partial" and {f.name: f.status for f in ctx.ops.list_files("FIN-C03-S2-F0118", 1)}["memo.docx"] == "failed"


def test_hints_bridge_the_internal_name_to_the_documents(small_blocks):
    """Golden g09 and g10: the documents never use the name Project Falcon; an approved hint does."""
    ctx = small_blocks
    do_upload(ctx, SARA, "FIN-C03-S2-F0118", sample_files(ctx, "FIN-C03-S2-F0118"))
    pump(ctx)
    from docai.security.access import access_scope
    scope = access_scope(ctx.ops.registered_groups(), LAYLA.groups)
    ask = lambda q: chat_api.answer(ctx, user_oid=LAYLA.oid, scope=scope, question=q)  # noqa: E731
    assert ask("What did we spend on Project Falcon?").abstained
    ev = chat_api.suggest_evidence(ctx, SARA, "Jebel Ali warehouse expansion cost centre 4410")
    hid = chat_api.submit_hint(ctx, SARA, department="FIN", type=chat_api.HintType.context_note, language="en",
                               text='"Project Falcon" was the internal name for the Jebel Ali warehouse expansion (CC 4410).',
                               evidence=[{"chunk_id": ev[0]["chunk_id"], "lines": [ev[0]["lines"][0]["ref"]]}])
    pump(ctx)
    rana = Principal("aaaaaaaa-0000-0000-0000-000000000002", "Rana", ["DocAI.Steward"], [FIN_READERS, "33333333-3333-3333-3333-333333333333"])
    review.approve_hint(ctx, rana, hid)
    pump(ctx)
    a = ask("What was the phase 1 budget for Project Falcon?")
    assert not a.abstained and "3.1M" in a.text and {c.document_id for c in a.citations} & {d.document_id for d in ctx.ops.list_documents("FIN-C03-S2-F0118", 1)}


# ---------------------------------------------------------------------------------------------- the watchdog
def run_to_ocr_only(ctx, dossier_id):
    """Uploads and runs the pipeline only as far as q-ocr-online, as if the OCR job were down."""
    h = load_handlers()
    do_upload(ctx, SARA, dossier_id, sample_files(ctx, dossier_id))
    for q in ("q-upload-commit", "q-intake", "q-preprocess"):
        process_queue(ctx, q, h[q])


def test_the_watchdog_resends_a_stalled_page_with_a_new_id_and_then_fails_it(ctx):
    clock = FixedClock()
    ctx.ops.clock = ctx.queue._clock = ctx.clock = clock
    dossier = "FIN-C07-S1-F0201"  # one page
    run_to_ocr_only(ctx, dossier)
    ocr = ctx.queue._entities["q-ocr-online"]
    assert len(ocr.live) == 1
    assert watchdog.run(ctx).resent == 0, "a page is not stuck before the limit"
    for attempt in (1, 2, 3):
        clock.advance(minutes=31)
        rep = watchdog.run(ctx)
        assert rep.resent == 1
        assert ("q-ocr-online", "page.ocr.requested", f"ocr:{dossier}@r1/p001:resend{attempt}") in ctx.queue.sent_log
    assert len(ocr.live) == 4, "the original and three resends: new IDs, so none was dropped as a duplicate"
    clock.advance(minutes=31)
    rep = watchdog.run(ctx)
    assert rep.failed_pages == 1 and rep.segment_sent == 1
    d = ctx.ops.get_dossier(dossier, 1)
    assert (d.pages_failed, d.status) == (1, "processing")
    lf = LinesFile.model_validate_json(ctx.blobs.read("extracted", keys.PageRef(dossier, 1, 1).dir + "lines.v1.json"))
    assert lf.lines[0].tier is TrustTier.missing and "stuck_after_resends" in lf.lines[0].text
    assert watchdog.run(ctx).failed_pages == 0, "a failed page is final: a second run changes nothing"


def test_a_page_message_that_used_all_five_deliveries_is_failed_so_the_dossier_does_not_wait(ctx):
    dossier = "FIN-C07-S1-F0201"
    run_to_ocr_only(ctx, dossier)
    h = load_handlers()
    ctx.ocr = type("Down", (), {"read": lambda *a, **k: (_ for _ in ()).throw(RuntimeError("OCR is down"))})()
    for _ in range(5):
        process_queue(ctx, "q-ocr-online", h["q-ocr-online"])
    assert ctx.queue.peek_dead_letters("q-ocr-online")
    rep = watchdog.run(ctx)
    assert rep.failed_pages == 1 and rep.dead_letters["q-ocr-online"] == 1
    pump(ctx)  # the closed revision continues: segmentation runs on the placeholder
    assert ctx.ops.get_dossier(dossier, 1).status == "failed", "every page failed, so the dossier failed and nothing was segmented"


def test_a_dossier_whose_files_never_matched_is_reported_as_failed_intake(ctx):
    do_upload(ctx, SARA, LEASE, {"a.pdf": pdf()})
    h = load_handlers()
    process_queue(ctx, "q-upload-commit", h["q-upload-commit"])
    ctx.blobs.write("raw", f"FIN/{LEASE}/a.pdf", b"tampered", overwrite=True)
    for _ in range(5):
        process_queue(ctx, "q-intake", h["q-intake"])
    rep = watchdog.run(ctx)
    assert rep.intake_failed == [LEASE]
    pump(ctx)
    assert any("failed" in r["title"] for r in ctx.ops.inbox_for(YOUSEF.oid, [], True))
    assert watchdog.run(ctx).intake_failed == [LEASE], "peeking leaves the dead letter in place for an operator"


def test_the_watchdog_also_purges_old_conversations_and_expires_abandoned_uploads(ctx):
    clock = FixedClock()
    ctx.ops.clock = ctx.queue._clock = ctx.clock = clock
    s = do_upload(ctx, SARA, LEASE, {"a.pdf": pdf()}, complete=False)
    ctx.ops.save_turn(answer_id="ans-1", conversation_id="c", user_oid="aaaaaaaa-0000-0000-0000-0000000000ff", question="q", answer="a", abstained=False, abstain_reason=None, intent=None,
                      language="en", evidence=[], verdict=None, scope_hash="h", latency_ms=1)
    clock.advance(days=91)
    rep = watchdog.run(ctx)
    assert rep.purged_conversations == 1 and rep.expired_uploads == 1 and ctx.ops.get_upload(s.upload_id)["status"] == "expired"
    with pytest.raises(UploadError):
        upload_api.put_block(ctx, SARA, s.upload_id, "a.pdf", 0, b"x")
