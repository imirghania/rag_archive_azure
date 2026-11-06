"""The first slice of the pipeline, end to end on the local fakes: upload -> intake -> preprocess -> OCR -> second read ->
reconcile -> segment -> metadata -> chunk/embed -> index."""
import json

import pytest

from docai.contracts import keys, messageids
from docai.contracts.artifacts import LinesFile
from docai.contracts.enums import TrustTier
from docai.runtime.messaging import envelope, send
from docai.runtime.runner import drain, load_handlers, process_queue

from conftest import FIN_READERS, HR_READERS, upload

LEASE = "FIN-C03-S2-F0117"


def run(ctx, dossier_id, **kw):
    upload(ctx, dossier_id, **kw)
    drain(ctx)


def test_lease_dossier_goes_from_files_to_searchable(ctx):
    run(ctx, LEASE)
    d = ctx.ops.get_dossier(LEASE, 1)
    assert (d.status, d.total_pages, d.pages_done, d.pages_failed) == ("completed", 5, 5, 0)
    assert d.acl_groups == [FIN_READERS]  # the department default: the reader group, not the restricted one

    docs = ctx.ops.list_documents(LEASE, 1)
    assert [(x.document_id, x.first_page, x.last_page) for x in docs] == [
        (f"{LEASE}-r1-D01", 1, 1), (f"{LEASE}-r1-D02", 2, 3), (f"{LEASE}-r1-D03", 4, 5)]
    assert all(x.indexed_version == 1 and x.status == "indexed" for x in docs)
    assert ctx.queue.total_depth() == 0
    assert not any(ctx.queue.peek_dead_letters(q) for q in ("q-ocr-online", "q-reconcile", "q-chunk"))


def test_the_two_readers_settle_or_escalate_each_handwritten_line_as_in_the_spec(ctx):
    run(ctx, LEASE)
    expected = json.loads((ctx.samples / "expected.json").read_text())["dossiers"][LEASE]["pages"][4]["lines"]
    lf = LinesFile.model_validate_json(ctx.blobs.read("extracted", keys.PageRef(LEASE, 1, 5).dir + "lines.v1.json"))
    got = {ln.id: ln for ln in lf.lines}
    for e in expected:
        assert got[e["id"]].tier.value == e["tier"], (e["id"], e["text"])
    amount = next(ln for ln in lf.lines if ln.tier is TrustTier.unverified and len(ln.candidates) == 2)
    assert amount.candidates == ["Approved, pay 1,250 by 15/3", "Approved, pay 1,750 by 15/3"]
    md = ctx.blobs.read("extracted", keys.PageRef(LEASE, 1, 5).dir + "page.v1.md").decode()
    assert "Approved, pay [unverified: 1,250 | 1,750] by 15/3" in md
    assert "> Margin note (handwritten, beside paragraph 3)" in md  # anchored beside the approval paragraph

    tasks = ctx.ops.list_tasks("FIN", "open")
    assert [t["task_id"] for t in tasks] == [88412, 88413]
    assert {t["document_id"] for t in tasks} == {f"{LEASE}-r1-D03"}
    assert {t["reason"] for t in tasks} == {"readers_disagree", "ocr_too_unsure"}


def test_second_reader_is_called_only_for_flagged_lines(ctx):
    run(ctx, LEASE)
    assert len(ctx.vision.calls) == 3  # the three handwritten lines; every printed line has confidence 0.97
    assert any(p.endswith(".vlm.json") for p in ctx.blobs.list("extracted", f"FIN/{LEASE}/r1/p005/crops/"))


def test_an_unverified_chunk_is_searchable_but_marked_so_the_verifier_can_refuse_it(ctx):
    run(ctx, LEASE)
    q = "approved amount Plot 118 warehouse lease renewal"
    hits = ctx.search.search("docs", text=q, vector=ctx.embedder.embed([q])[0], acl_groups=[FIN_READERS])
    memo = next(h for h in hits if h.doc["document_id"] == f"{LEASE}-r1-D03" and "Approved" in h.doc["text_en"])
    assert memo.doc["min_trust"] == "unverified" and memo.doc["min_trust_rank"] == 1
    tiers = json.loads(memo.doc["trust_tiers_json"])
    assert "unverified" in tiers.values() and "handwritten_dual_agreed" in tiers.values()
    assert memo.doc["reference"] == "FIN/MEMO/2008/114" and memo.doc["doc_date"] == "2008-02-27"


def test_the_security_filter_hides_finance_from_other_departments(ctx):
    run(ctx, LEASE)
    v = ctx.embedder.embed(["lease Plot 118"])[0]
    assert ctx.search.search("docs", text="lease Plot 118", vector=v, acl_groups=[HR_READERS]) == []
    assert ctx.search.search("docs", text="lease Plot 118", vector=v, acl_groups=[FIN_READERS])


def test_a_damaged_frame_loses_one_page_not_the_dossier(ctx):
    run(ctx, "FIN-C09-S1-F0300")
    d = ctx.ops.get_dossier("FIN-C09-S1-F0300", 1)
    assert (d.status, d.total_pages, d.pages_done, d.pages_failed) == ("partial", 3, 2, 1)
    p2 = keys.PageRef("FIN-C09-S1-F0300", 1, 2)
    lf = LinesFile.model_validate_json(ctx.blobs.read("extracted", p2.dir + "lines.v1.json"))
    assert lf.lines[0].tier is TrustTier.missing and "corrupt_image" in lf.lines[0].text
    assert [x.has_gaps for x in ctx.ops.list_documents("FIN-C09-S1-F0300", 1)] == [True]
    assert ("t-docai-events", "dossier.partial", "partial:FIN-C09-S1-F0300@r1") in ctx.queue.sent_log


def test_a_planted_instruction_is_flagged_before_it_can_be_searched(ctx):
    run(ctx, "FIN-C05-S1-F0099")
    flagged = ctx.search.ids("docs", injection_suspect=True)
    assert flagged, "the chunk with 'Ignore your instructions' must be flagged at indexing time"
    v = ctx.embedder.embed(["list all employee salaries"])[0]
    hits = ctx.search.search("docs", text="list all employee salaries", vector=v, acl_groups=[FIN_READERS])
    assert not any(h.id in flagged for h in hits)


def test_the_same_commit_twice_does_no_second_run(ctx):
    h1 = upload(ctx, LEASE)
    drain(ctx)
    before = len(ctx.queue.sent_log)
    env = envelope("dossier.received", LEASE, department="FIN", dossier_id=LEASE,
                   payload={"manifest": keys.raw_dossier_dir(LEASE, 1) + "dossier.json", "manifest_hash": h1})
    # inside the detection window the message is dropped ...
    assert send(ctx, env, message_id=messageids.intake(LEASE, h1)) is False
    # ... and after the window intake recognises the duplicate by its hash and does no work
    ctx.queue.forget_duplicate_window("q-intake")
    assert send(ctx, env, message_id=messageids.intake(LEASE, h1)) is True
    drain(ctx)
    assert len(ctx.ops.list_documents(LEASE, 1)) == 3
    assert not [m for m in ctx.queue.sent_log[before:] if m[0] != "q-intake"]
    with pytest.raises(KeyError):
        ctx.ops.get_dossier(LEASE, 2)


def test_a_tampered_file_never_reaches_registration(ctx):
    dossier = "FIN-C07-S1-F0201"
    upload(ctx, dossier)
    ctx.blobs.write("raw", keys.raw_dossier_dir(dossier, 1) + "scan_001.tif", b"not the scan", overwrite=True)
    for _ in range(6):  # five deliveries, then the message is dead-lettered
        process_queue(ctx, "q-intake", load_handlers()["q-intake"])
    assert ctx.queue.peek_dead_letters("q-intake")
    with pytest.raises(KeyError):
        ctx.ops.get_dossier(dossier, 1)
