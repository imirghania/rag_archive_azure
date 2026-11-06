import pytest

from docai.contracts import keys, messageids
from docai.contracts.artifacts import LinesFile
from docai.contracts.enums import TrustTier, min_tier
from docai.contracts.messages import (
    QUEUES, ROUTES, Envelope, destination_of, parse_payload, session_of,
)


def test_key_roundtrip_and_revision_is_part_of_every_key():
    page = keys.page_key("FIN-C03-S2-F0117", 1, 14)
    assert page == "FIN-C03-S2-F0117@r1/p014"
    ref = keys.PageRef.parse(page)
    assert (ref.revision, ref.page_no, ref.department) == (1, 14, "FIN")
    assert ref.dir == "FIN/FIN-C03-S2-F0117/r1/p014/"
    lk = keys.LineRef.parse(keys.line_key(page, "L17"))
    assert lk.short == "p014/L17"
    assert keys.PageRef.parse(keys.page_key("FIN-C03-S2-F0117", 2, 14)).key != page


def test_document_and_chunk_ids_are_valid_search_keys():
    doc = keys.document_id("FIN-C03-S2-F0117", 1, 3)
    cid = keys.chunk_id(doc, 1, 2)
    assert cid == "FIN-C03-S2-F0117-r1-D03__v1__c0002"
    assert keys.SEARCH_KEY_RE.match(cid)
    assert keys.parse_chunk_id(cid) == (doc, 1, 2)


def test_unfiled_dossier_department():
    assert keys.department_of("UNF-FIN-20261104-0007") == "FIN"


@pytest.mark.parametrize("bad", ["FIN-C03-S2-F0117@r0", "fin-c03", "FIN-C03-S2-F0117/p014"])
def test_malformed_keys_are_rejected(bad):
    with pytest.raises(ValueError):
        keys.parse_dossier_key(bad)


def test_resend_suffixes_change_the_id():
    mid = messageids.message_id("ocr", "FIN-C03-S2-F0117@r1/p014")
    assert messageids.resend(mid, 1) != mid
    assert messageids.retry_try(mid, 2).endswith(":try2")
    with pytest.raises(ValueError):
        messageids.retry_try(mid, 1)
    assert messageids.reprocess("FIN-C03-S2-F0117", 2) == "reprocess:FIN-C03-S2-F0117:r2"


def test_trust_tiers_follow_the_table():
    assert not TrustTier.unverified.citable
    assert TrustTier.handwritten_dual_agreed.citable
    assert TrustTier.human_verified.rank == 7
    assert min_tier([TrustTier.human_verified, TrustTier.unverified]) is TrustTier.unverified
    assert min_tier([]) is TrustTier.missing


def test_every_route_points_to_a_known_queue_and_has_a_payload_contract():
    from docai.contracts.messages import PAYLOADS
    assert set(ROUTES.values()) <= set(QUEUES)
    assert set(ROUTES) <= set(PAYLOADS)
    assert len(QUEUES) == 13
    assert session_of("q-chunk", "FIN-C03-S2-F0117-r1-D03") == "FIN-C03-S2-F0117-r1-D03"
    assert session_of("q-ocr-online", "x") is None
    assert destination_of("document.indexed") == "t-docai-events"


def test_envelope_roundtrip_serializes_schema_number():
    env = Envelope(type="page.ocr.requested", subject="FIN-C03-S2-F0117@r1/p014",
                   dossier_id="FIN-C03-S2-F0117", revision=1, department="FIN",
                   payload={"page_no": 14, "page_dir": "x/"})
    assert '"schema":1' in env.to_json()
    again = Envelope.from_json(env.to_json())
    assert parse_payload(again).page_no == 14


def test_readers_ignore_fields_added_by_a_newer_writer():
    lf = LinesFile.model_validate({
        "schema": 1, "page_key": "FIN-C03-S2-F0117@r1/p014", "page_no": 14, "new_field": "x",
        "lines": [{"id": "L1", "text": "t", "tier": "printed_high_conf", "style": "printed",
                   "box": {"x0": 0, "y0": 0, "x1": 1, "y1": 1}, "future": 1}]})
    assert lf.line("L1").tier is TrustTier.printed_high_conf
