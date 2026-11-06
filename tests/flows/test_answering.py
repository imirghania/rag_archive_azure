"""Workflow 6 on the local fakes: the golden questions, the verifier layers, the security filter and the demand loop."""
import json

import pytest

from docai.security.access import access_scope
from docai.contracts.enums import Decision
from docai.modules import chat_api, review
from docai.modules.verifier import numbers, split_claims
from docai.runtime.runner import drain

from conftest import FIN_EXPERTS, FIN_READERS, FIN_TREASURY, HR_READERS, upload

LEASE, TREASURY, HR, PLANTED = "FIN-C03-S2-F0117", "FIN-C07-S1-F0201", "HR-C01-S1-F0010", "FIN-C05-S1-F0099"
USERS = {"layla": [FIN_READERS], "sara": [FIN_READERS, FIN_EXPERTS, FIN_TREASURY], "huda": [HR_READERS]}
OID = {"layla": "aaaaaaaa-0000-0000-0000-00000000000a", "sara": "aaaaaaaa-0000-0000-0000-000000000001", "huda": "aaaaaaaa-0000-0000-0000-00000000000b"}


@pytest.fixture
def world(ctx):
    for d in (LEASE, TREASURY, HR, PLANTED):
        upload(ctx, d)
    drain(ctx)
    # the treasury dossier is restricted to the treasury group (Workflow 8): index messages follow through the outbox
    ctx.ops.change_dossier_acl(TREASURY, [FIN_TREASURY], "R. Saleh", "Treasury only per policy TR-04")
    review.relay_outbox(ctx)
    drain(ctx)
    return ctx


def ask(ctx, user, question, conv=None):
    scope = access_scope(ctx.ops.registered_groups(), USERS[user])
    return chat_api.answer(ctx, user_oid=OID[user], scope=scope, question=question, conversation_id=conv)


def settle_amount(ctx):
    t = ctx.ops.claim_task(OID["sara"], ["FIN"])
    while t and t["line_id"] != "L8":  # the amount line
        t = ctx.ops.claim_task(OID["sara"], ["FIN"])
    review.decide(ctx, task_id=t["task_id"], lease_token=t["lease_token"], user_oid=OID["sara"], user_name="Sara", departments=["FIN"], decision=Decision.accept_model)
    review.relay_outbox(ctx)
    drain(ctx)


def golden(ctx):
    return [json.loads(x) for x in (ctx.samples / "golden.jsonl").read_text(encoding="utf-8").splitlines()]


def check(ctx, g, a):
    e = g["expect"]
    if e["behavior"] == "answer":
        assert not a.abstained, (g["id"], a.text)
        for s in e.get("contains", []):
            assert s in a.text, (g["id"], a.text)
        docs = {c.document_id for c in a.citations}
        if "cites_doc" in e:
            assert e["cites_doc"] in docs, (g["id"], docs)
        if "cites_doc_any" in e:
            assert docs & set(e["cites_doc_any"]), (g["id"], docs)
    elif e["behavior"] == "abstain":
        assert a.abstained and not a.citations, (g["id"], a.text)
        assert a.text == chat_api.MESSAGES["en"]["no_evidence"], "the reply must not reveal why (or that a document exists)"
    elif e["behavior"] == "partial":
        assert a.abstained and a.reason == "unverified" and a.needs_review and "awaiting expert verification" in a.text
        for s in e.get("must_not_contain", []):
            assert s not in a.text
    elif e["behavior"] == "out_of_scope":
        assert a.intent == "out_of_scope" and a.abstained and not a.citations


SKIPPED = {"g03": "answer language needs a real model", "g09": "covered by test_upload_flow.test_hints_bridge_the_internal_name_to_the_documents", "g10": "covered by the same test"}


def test_golden_questions_before_review(world):
    for g in golden(world):
        if g["phase"] in ("before_review", "any") and g["id"] not in SKIPPED:
            check(world, g, ask(world, g["user"], g["question"]))


def test_golden_questions_after_review(world):
    settle_amount(world)
    for g in golden(world):
        if g["phase"] == "after_review" and g["id"] not in SKIPPED:
            check(world, g, ask(world, g["user"], g["question"]))


def test_arabic_question_finds_the_english_memo_and_the_quote_stays_in_the_source_language(world):
    settle_amount(world)
    a = ask(world, "layla", "كم المبلغ المعتمد لتجديد عقد إيجار القطعة 118؟")
    assert not a.abstained and "1,750" in a.text and a.language == "ar"
    assert {c.document_id for c in a.citations} == {f"{LEASE}-r1-D03"}


def test_a_blocked_answer_moves_the_review_queue(world):
    """The refusal is recorded as a blocked hit, which is how the line comes to the front (Workflow 4, Step 2)."""
    world.ops.record_demand([{"line_key": world.ops.get_task(88413)["line_key"], "kind": "retrieved"}])  # a little demand for the Arabic note
    a = ask(world, "layla", "How much was approved for the Plot 118 lease renewal?")  # blocks the amount line, task 88412
    assert a.abstained and a.reason == "unverified"
    blocked = [r["line_key"] for r in world.ops.debug_rows("review_demand", kind="blocked", answer_id=a.answer_id)]
    assert blocked == [world.ops.get_task(88412)["line_key"]]
    assert review.claim_next(world, OID["sara"], ["FIN"])["task_id"] == 88412, "10 for a blocked hit outranks 1 for a retrieved hit"


def test_scope_filter_is_applied_by_retrieval_and_users_never_pass_it_to_the_model(world):
    seen = []
    orig = world.agent.run

    def spy(**kw):
        seen.append(json.dumps({k: v for k, v in kw.items() if k != "tools"}, default=str))
        return orig(**kw)
    world.agent.run = spy
    ask(world, "huda", "How much was approved for the Plot 118 lease renewal?")
    assert seen and not any(g in s for s in seen for g in (HR_READERS, FIN_READERS, FIN_TREASURY))


def test_a_planted_instruction_found_at_query_time_is_dropped_flagged_and_left_for_a_steward(world):
    for cid in [c for c in world.search.ids("docs") if c.startswith(PLANTED)]:
        world.search.merge("docs", {"chunk_id": cid, "injection_suspect": False})  # as if the index had not caught it yet
    a = ask(world, "layla", "What did the complaint letter say about invoice INV-3301 and the vendor?")
    assert a.abstained and a.reason == "flagged_content" and not a.citations
    drain(world)
    assert [c for c in world.search.ids("docs", injection_suspect=True) if c.startswith(PLANTED)]
    assert len(world.ops.debug_rows("content_flags")) >= 1


def test_follow_up_questions_keep_the_conversation_and_history_is_per_user(world):
    settle_amount(world)
    a = ask(world, "layla", "How much was approved for the Plot 118 lease renewal?")
    assert world.ops.history(a.conversation_id, OID["layla"]) and world.ops.history(a.conversation_id, OID["huda"]) == []
    b = ask(world, "layla", "Who initialled it?", conv=a.conversation_id)
    assert b.conversation_id == a.conversation_id and len(world.ops.history(a.conversation_id, OID["layla"])) == 2


def test_conversations_older_than_the_retention_period_are_purged(world):
    from docai.adapters.local.clock import FixedClock
    clock = FixedClock()
    world.ops.clock = clock
    ask(world, "layla", "How much was approved for the Plot 118 lease renewal?")
    clock.advance(days=91)
    ask(world, "layla", "What was the annual rent in the Plot 118 lease agreement?")
    assert world.ops.purge_conversations(90) == 1
    assert len(world.ops.debug_rows("conversations")) == 1


# ------------------------------------------------------------------ the verifier layers, one by one
LINE_REF = "p005/L8"
CHUNK = "FIN-C03-S2-F0117-r1-D03__v2__c0002"


def ev(tier="human_verified", text="Approved, pay 1,750 by 15/3", acl=None):
    return {CHUNK: {"chunk_id": CHUNK, "acl_groups": acl or [FIN_READERS], "trust_tiers_json": json.dumps({LINE_REF: tier}),
                    "lines": [{"ref": LINE_REF, "text": text}]}}


def verify(ctx, draft, evidence, scope=None):
    return ctx.verifier.verify(draft=draft, evidence=evidence, scope=scope or [FIN_READERS])


def test_verifier_passes_a_cited_checked_claim(ctx):
    v = verify(ctx, f"Approved, pay 1,750 by 15/3 [c:{CHUNK}#{LINE_REF}].", ev())
    assert v.ok and v.supported[0].citations == [f"{CHUNK}#{LINE_REF}"]


@pytest.mark.parametrize("draft,evidence,scope,layer", [
    ("Approved, pay 1,750 by 15/3.", ev(), None, "structure"),  # no citation
    ("Approved [c:OTHER-r1-D01__v1__c0001#p001/L1].", ev(), None, "structure"),  # chunk not returned in this run
    (f"Approved, pay 1,750 by 15/3 [c:{CHUNK}#{LINE_REF}].", ev(), [HR_READERS], "structure"),  # chunk outside the caller's scope
    (f"Approved, pay 1,750 by 15/3 [c:{CHUNK}#{LINE_REF}].", ev(tier="unverified"), None, "trust_tier"),
    (f"Approved, pay 1,250 by 15/3 [c:{CHUNK}#{LINE_REF}].", ev(), None, "numbers"),  # 1,250 is not in the cited line
    (f"Approved on 15 March [c:{CHUNK}#{LINE_REF}].", ev(), None, "entailment"),  # the spec example: the line says 15/3, no month
])
def test_each_verifier_layer_refuses_what_it_is_for(ctx, draft, evidence, scope, layer):
    v = verify(ctx, draft, evidence, scope)
    assert not v.ok and v.claims[0].failed_layer == layer, v.claims[0]


def test_a_refused_unverified_line_is_reported_as_blocked(ctx):
    v = verify(ctx, f"Approved, pay 1,750 by 15/3 [c:{CHUNK}#{LINE_REF}].", ev(tier="unverified"))
    assert v.blocked_lines == [f"FIN-C03-S2-F0117@r1/{LINE_REF}"]


def test_citation_markers_in_the_middle_of_a_sentence_and_after_the_period_belong_to_the_same_claim():
    d = "The renewal was approved for 1,750 [c:A#p1/L1], in a note [c:A#p1/L2] on the memo dated 27 February 2008 [c:B#p1/L3]. [c:B#p1/L4]"
    claims = split_claims(d)
    assert len(claims) == 1 and claims[0].count("[c:") == 4
    assert numbers("approved for 1,750 and ١٬٧٥٠ in 2008 [c:A#p1/L1]") == {"1,750", "2008"}
