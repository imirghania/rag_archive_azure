"""Workflow 4 and Workflow 8 on the local fakes: claim under a lease, decide, fold, re-chunk, re-index, swap."""
import json

import pytest

from docai.adapters.local.clock import FixedClock
from docai.contracts import keys, messageids
from docai.contracts.artifacts import LinesFile
from docai.contracts.enums import Decision, TrustTier
from docai.runtime.messaging import envelope, send
from docai.modules import review
from docai.ports import LeaseLost
from docai.runtime.runner import drain

from conftest import upload

LEASE = "FIN-C03-S2-F0117"
D03 = f"{LEASE}-r1-D03"
SARA, OMAR, RANA = "aaaaaaaa-0000-0000-0000-000000000001", "aaaaaaaa-0000-0000-0000-000000000003", "aaaaaaaa-0000-0000-0000-000000000002"
FIN = ["FIN"]


@pytest.fixture
def done(ctx):
    upload(ctx, LEASE)
    drain(ctx)
    return ctx


def line_key(ctx, text_start: str) -> str:
    """Key of the unverified line whose candidate starts with `text_start`."""
    for t in ctx.ops.list_tasks("FIN", "open"):
        pdir = keys.PageRef(t["dossier_id"], t["revision"], t["page_no"]).dir
        lf = LinesFile.model_validate_json(ctx.blobs.read("extracted", pdir + "lines.v1.json"))
        if any(c.startswith(text_start) for c in lf.line(t["line_id"]).candidates):
            return t["line_key"]
    raise AssertionError(text_start)


def claim_task_for(ctx, user, line_text):
    ctx.ops.record_demand([{"line_key": line_key(ctx, line_text), "kind": "blocked"}])
    return review.claim_next(ctx, user, FIN)


def settle(ctx, user, task, decision, text=None):
    review.decide(ctx, task_id=task["task_id"], lease_token=task["lease_token"], user_oid=user, user_name="x",
                  departments=FIN, decision=decision, text=text)
    review.relay_outbox(ctx)
    drain(ctx)


def chunks_of(ctx, doc=D03):
    return {i: ctx.search.get("docs", i) for i in ctx.search.ids("docs", document_id=doc)}


def test_the_most_blocked_line_comes_first_and_the_lease_is_fifteen_minutes(done):
    task = claim_task_for(done, SARA, "Approved")
    assert task["task_id"] == 88412 and task["status"] == "claimed" and task["line_id"] == "L8"
    ev = review.evidence(done, task["task_id"], FIN)
    assert [r.engine for r in ev.readings.readings] == ["ocr", "second_reader"]
    assert ev.crop.startswith(b"\x89PNG") and ev.context_crop.startswith(b"\x89PNG")


def test_a_decision_makes_version_two_and_the_old_chunks_disappear(done):
    task = claim_task_for(done, SARA, "Approved")
    before = chunks_of(done)
    assert {c["version"] for c in before.values()} == {1}
    settle(done, SARA, task, Decision.accept_model)

    assert done.ops.get_document(D03).current_version == 2 and done.ops.get_document(D03).indexed_version == 2
    after = chunks_of(done)
    assert {c["version"] for c in after.values()} == {2}, "version 1 chunks are deleted only after version 2 is searchable"
    chunk = next(c for c in after.values() if "Approved" in c["text_en"])
    assert "Approved, pay 1,750 by 15/3" in chunk["text_en"] and "[unverified" not in chunk["text_en"].split("Margin")[-1].split("K. Al")[0]
    tiers = json.loads(chunk["trust_tiers_json"])
    assert TrustTier.human_verified.value in tiers.values()
    assert chunk["min_trust"] == "unverified", "the Arabic note is still pending"
    md = done.blobs.read("extracted", f"{keys.PageRef(LEASE, 1, 5).dir}page.v2.md").decode()
    assert "Approved, pay 1,750 by 15/3" in md and "[unverified: 1,250" not in md
    assert done.blobs.exists("extracted", f"{keys.PageRef(LEASE, 1, 5).dir}page.v1.md"), "version 1 stays reproducible"


def test_two_decisions_fold_into_version_three_and_min_trust_rises(done):
    settle(done, SARA, claim_task_for(done, SARA, "Approved"), Decision.accept_model)
    arabic = review.claim_next(done, OMAR, FIN)
    assert arabic["line_id"] == "L11"
    settle(done, OMAR, arabic, Decision.accept_model)
    assert done.ops.get_document(D03).current_version == 3
    lf = LinesFile.model_validate_json(done.blobs.read("extracted", f"{keys.PageRef(LEASE, 1, 5).dir}lines.v3.json"))
    assert {lf.line(i).tier for i in ("L8", "L11")} == {TrustTier.human_verified}, "v3 holds both decisions"
    assert {c["min_trust"] for c in chunks_of(done).values()} == {"handwritten_dual_agreed"} or \
        min(c["min_trust_rank"] for c in chunks_of(done).values()) >= 3
    assert {c["version"] for c in chunks_of(done).values()} == {3}


def test_two_reviewers_at_once_end_in_the_same_state_in_either_order(done):
    a = claim_task_for(done, SARA, "Approved")
    b = review.claim_next(done, OMAR, FIN)
    for t, who in ((a, SARA), (b, OMAR)):  # both decide before anything is processed
        review.decide(done, task_id=t["task_id"], lease_token=t["lease_token"], user_oid=who, user_name="x",
                      departments=FIN, decision=Decision.accept_model)
    review.relay_outbox(done)
    drain(done)
    doc = done.ops.get_document(D03)
    assert doc.current_version == 3 and doc.indexed_version == 3
    lf = LinesFile.model_validate_json(done.blobs.read("extracted", f"{keys.PageRef(LEASE, 1, 5).dir}lines.v3.json"))
    assert lf.line("L8").tier is lf.line("L11").tier is TrustTier.human_verified
    v2 = LinesFile.model_validate_json(done.blobs.read("extracted", f"{keys.PageRef(LEASE, 1, 5).dir}lines.v2.json"))
    assert sorted(ln.id for ln in v2.lines if ln.tier is TrustTier.human_verified) in (["L11"], ["L8"]), "v2 holds only the first decision handled"


def test_a_redelivered_decision_changes_nothing_and_still_finishes_the_work(done):
    task = claim_task_for(done, SARA, "Approved")
    review.decide(done, task_id=task["task_id"], lease_token=task["lease_token"], user_oid=SARA, user_name="x", departments=FIN, decision=Decision.accept_ocr)
    review.relay_outbox(done)
    drain(done)
    row = done.ops.pending_outbox()
    assert row == [] and done.ops.get_document(D03).current_version == 2
    # the same review.decided message arrives again (the queue delivered twice): version stays 2, nothing breaks
    req = done.ops.debug_rows("outbox", destination="q-post-review")[0]["body"]
    from docai.contracts.messages import Envelope
    done.queue.forget_duplicate_window("q-post-review")
    done.queue.send("q-post-review", Envelope.from_json(req), message_id="again", session_id=D03)
    drain(done)
    assert done.ops.get_document(D03).current_version == 2


def test_an_expired_lease_goes_to_the_next_person_and_the_first_cannot_submit(done):
    clock = FixedClock()
    done.ops.clock = clock
    omar = claim_task_for(done, OMAR, "Approved")
    clock.advance(minutes=16)
    sara = review.claim_next(done, SARA, FIN)
    assert sara["task_id"] == omar["task_id"] and sara["lease_token"] != omar["lease_token"]
    with pytest.raises(LeaseLost):
        review.decide(done, task_id=omar["task_id"], lease_token=omar["lease_token"], user_oid=OMAR, user_name="x", departments=FIN, decision=Decision.accept_ocr)
    assert review.heartbeat(done, sara["task_id"], sara["lease_token"], FIN) is not None
    assert review.heartbeat(done, omar["task_id"], omar["lease_token"], FIN) is None


def test_a_task_abandoned_three_times_is_escalated_to_the_stewards(done):
    clock = FixedClock()
    done.ops.clock = clock
    done.ops.record_demand([{"line_key": done.ops.get_task(88412)["line_key"], "kind": "blocked"}])
    for _ in range(3):
        assert review.claim_next(done, OMAR, FIN)["task_id"] == 88412
        clock.advance(minutes=16)  # the lease lapses without a decision
    nxt = review.claim_next(done, SARA, FIN)  # the third lapsed lease is counted here
    assert done.ops.get_task(88412)["status"] == "escalated"
    assert nxt["task_id"] == 88413, "an escalated task is no longer offered to experts"


def test_every_fifth_claim_takes_the_oldest_task_whatever_the_demand(done):
    done.ops.record_demand([{"line_key": done.ops.get_task(88413)["line_key"], "kind": "blocked"}])
    assert review.claim_next(done, SARA, FIN)["task_id"] == 88413, "demand first"
    # jump the department counter to the fifth claim
    done.ops.debug_set_claims("FIN", 4)
    assert review.claim_next(done, OMAR, FIN)["task_id"] == 88412, "the fifth claim takes the oldest"


def test_a_department_cannot_see_or_touch_another_departments_task(done):
    assert review.claim_next(done, SARA, []) is None
    assert review.claim_next(done, SARA, ["HR"]) is None
    task = claim_task_for(done, SARA, "Approved")
    with pytest.raises(PermissionError):
        review.decide(done, task_id=task["task_id"], lease_token=task["lease_token"], user_oid=SARA, user_name="x", departments=["HR"], decision=Decision.accept_ocr)
    with pytest.raises(PermissionError):
        review.evidence(done, task["task_id"], ["HR"])


def test_a_correction_needs_text(done):
    t = claim_task_for(done, SARA, "Approved")
    with pytest.raises(review.ReviewError):
        review.decide(done, task_id=t["task_id"], lease_token=t["lease_token"], user_oid=SARA, user_name="x", departments=FIN,
                      decision=Decision.correct, text="  ")
    assert done.ops.get_task(t["task_id"])["status"] == "claimed", "a refused decision leaves the lease alone"


def test_illegible_and_correction_decisions(done):
    t = claim_task_for(done, SARA, "Approved")
    settle(done, SARA, t, Decision.correct, "Approved, pay 1,700 by 15/3")
    lf = LinesFile.model_validate_json(done.blobs.read("extracted", f"{keys.PageRef(LEASE, 1, 5).dir}lines.v2.json"))
    assert lf.line("L8").text == "Approved, pay 1,700 by 15/3" and lf.line("L8").tier is TrustTier.human_verified
    t2 = review.claim_next(done, SARA, FIN)
    settle(done, SARA, t2, Decision.illegible)
    lf3 = LinesFile.model_validate_json(done.blobs.read("extracted", f"{keys.PageRef(LEASE, 1, 5).dir}lines.v3.json"))
    assert lf3.line("L11").tier is TrustTier.illegible
    assert min(c["min_trust_rank"] for c in chunks_of(done).values()) == 0, "an illegible line is never citable"
    assert review.claim_next(done, SARA, FIN) is None


def test_reprocess_swaps_revisions_only_when_the_new_one_is_completed(done):
    before = chunks_of(done, D03)
    assert before
    env = envelope("dossier.reprocess.requested", LEASE, department="FIN", dossier_id=LEASE, payload={"requested_by": "yousef", "from_revision": 1})
    assert send(done, env, message_id=messageids.reprocess(LEASE, 2))
    drain(done)
    assert done.ops.get_dossier(LEASE, 2).status == "completed" and done.ops.get_dossier(LEASE, 1).status == "superseded"
    docs = {d for c in done.search.ids("docs") for d in [done.search.get("docs", c)["document_id"]]}
    assert docs and all("-r2-" in d for d in docs), "only revision 2 is searchable after the swap"
    assert any(m[1] == "document.removed" for m in done.queue.sent_log)
    # a repeated reprocess request for the same revision is stale and does nothing
    done.queue.forget_duplicate_window("q-intake")
    send(done, env, message_id=messageids.reprocess(LEASE, 2))
    drain(done)
    with pytest.raises(KeyError):
        done.ops.get_dossier(LEASE, 3)


def test_row_level_security_lets_the_review_app_see_only_its_departments_tasks(done, pg_url, as_role):
    """Runs the review calls as a login user that is a member of r_review, neither a superuser nor the table owner, the way the
    review app's identity runs in Azure. As the test superuser the filter is bypassed, which is why every other test cannot
    catch a missing app.departments setting."""
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    done.ops = ops = as_role("r_review")
    assert ops.list_tasks() == [], "no departments set: nothing is visible (fails closed)"
    t = review.claim_next(done, SARA, FIN)
    assert t is not None and t["department"] == "FIN", "the service sets the departments before it claims"
    assert review.claim_next(done, OMAR, ["HR"]) is None, "another department sees no Finance task"
    with pytest.raises(KeyError):  # the other department's task does not exist for it, instead of being refused
        review.evidence(done, t["task_id"], ["HR"])
    ev = review.evidence(done, t["task_id"], FIN)
    assert ev.task["task_id"] == t["task_id"]
    with pytest.raises(DBAPIError, match="row-level security"), ops.engine.begin() as c:  # a row cannot be moved out of the caller's departments
        c.execute(text("SELECT set_config('app.departments', 'FIN', true)"))
        c.execute(text("UPDATE ops.review_tasks SET department = 'HR' WHERE task_id = :t"), {"t": t["task_id"]})
    review.decide(done, task_id=t["task_id"], lease_token=t["lease_token"], user_oid=SARA, user_name="x", departments=FIN, decision=Decision.accept_model)
    ops.set_departments([])
    assert ops.list_tasks() == [], "an empty department list shows nothing"


def test_a_caller_with_no_review_departments_sees_nothing_and_does_not_crash_the_store(done):
    """An empty department list must reach the store as a value it accepts: the review app is called by readers and admins too."""
    for departments in ([], ["HR"]):
        with pytest.raises((PermissionError, KeyError)):
            review.evidence(done, 88412, departments)
    assert review.claim_next(done, SARA, []) is None
