"""Workflow 5 on the local fakes: submit, check, approve, publish, follow access changes, reject, revoke, transcription fix."""
import pytest

from docai.security.access import Principal
from docai.adapters.local.clock import FixedClock
from docai.contracts import keys
from docai.contracts.artifacts import LinesFile
from docai.contracts.enums import Decision, HintType, TrustTier
from docai.modules import chat_api, review
from docai.runtime.runner import drain

from conftest import FIN_EXPERTS, FIN_READERS, FIN_STEWARDS, FIN_TREASURY, upload

LEASE, TREASURY = "FIN-C03-S2-F0117", "FIN-C07-S1-F0201"
SARA = Principal("aaaaaaaa-0000-0000-0000-000000000001", "Sara Aziz", ["DocAI.Expert"], [FIN_READERS, FIN_EXPERTS, FIN_TREASURY])
OMAR = Principal("aaaaaaaa-0000-0000-0000-000000000003", "Omar", ["DocAI.Expert"], [FIN_READERS, FIN_EXPERTS])
RANA = Principal("aaaaaaaa-0000-0000-0000-000000000002", "Rana Saleh", ["DocAI.Steward"], [FIN_READERS, FIN_STEWARDS])
LAYLA = Principal("aaaaaaaa-0000-0000-0000-00000000000a", "Layla", ["DocAI.Reader"], [FIN_READERS])
TEXT = '"Project Falcon" was the internal name used 2006-2009 for the Jebel Ali warehouse expansion.'


def pump(ctx):
    """Relays the outbox and runs every consumer until nothing moves (the relay loop of app-review plus KEDA)."""
    for _ in range(10):
        n = review.relay_outbox(ctx)
        n += drain(ctx)
        if n == 0:
            return


@pytest.fixture
def world(ctx):
    upload(ctx, LEASE)
    upload(ctx, TREASURY)
    pump(ctx)
    return ctx


def evidence_for(ctx, p, text="Jebel Ali warehouse"):
    s = chat_api.suggest_evidence(ctx, p, text)
    assert s, "the hint's own vocabulary finds the document"
    return [{"chunk_id": s[0]["chunk_id"], "lines": [s[0]["lines"][0]["ref"]]}]


def submit(ctx, p=SARA, type=HintType.context_note, text=TEXT, **kw):
    return chat_api.submit_hint(ctx, p, department="FIN", type=type, language="en", text=text, **kw)


def test_a_hint_travels_from_submission_to_the_notes_index_and_the_authors_inbox(world):
    hid = submit(world, evidence=evidence_for(world, SARA))
    assert hid == "hint-000731" and world.ops.get_hint(hid)["status"] == "submitted"
    pump(world)
    h = world.ops.get_hint(hid)
    assert h["status"] == "awaiting_approval" and h["check_results"]["prompt_shields"] is False
    assert h["author_oid"] == SARA.oid and h["evidence_status"] == "documentary" and h["evidence"][0]["quote"]
    assert world.search.get("notes", hid) is None, "nothing is searchable before a steward approves"

    assert [x["hint_id"] for x in review.hints_awaiting(world, RANA)] == [hid]
    assert review.hints_awaiting(world, SARA) == [], "an expert has no approval queue"
    review.approve_hint(world, RANA, hid)
    pump(world)
    note = world.search.get(hid and "notes", hid)
    assert world.ops.get_hint(hid)["status"] == "published" and note["acl_groups"] == [FIN_READERS]
    assert note["approved_by"] == "Rana Saleh" and note["evidence_status"] == "documentary"
    inbox = world.ops.inbox_for(SARA.oid, [], False)
    assert len(inbox) == 1 and "approved by Rana Saleh" in inbox[0]["title"]
    assert len(world.ops.debug_rows("hint_publications")) == 1


def test_an_approved_note_is_found_by_a_question_that_uses_the_internal_name(world):
    hid = submit(world, evidence=evidence_for(world, SARA))
    pump(world)
    review.approve_hint(world, RANA, hid)
    pump(world)
    from docai.security.access import access_scope
    scope = access_scope(world.ops.registered_groups(), LAYLA.groups)
    notes = world.retrieval.search_notes(scope=scope, query="Project Falcon")
    assert notes and notes[0]["hint_id"] == hid and "Jebel Ali" in notes[0]["text"] and notes[0]["approved_by"] == "Rana Saleh"


def test_the_author_cannot_approve_and_an_expert_cannot_approve_at_all(world):
    hid = submit(world)
    pump(world)
    with pytest.raises(PermissionError):
        review.approve_hint(world, SARA, hid)  # not a steward
    steward_author = Principal(RANA.oid, "Rana", ["DocAI.Steward", "DocAI.Expert"], [FIN_READERS, FIN_STEWARDS, FIN_EXPERTS])
    own = submit(world, steward_author, text="Cost centre 4410 covers the warehouse expansion.")
    pump(world)
    with pytest.raises(PermissionError, match="author"):
        review.approve_hint(world, steward_author, own)  # four eyes: enforced by the store, not only by a hidden button
    assert world.ops.get_hint(own)["status"] == "awaiting_approval"


def test_a_tacit_hint_has_no_evidence_and_says_so(world):
    hid = submit(world, text="The CFO prefers quarterly rent payments.")
    assert world.ops.get_hint(hid)["evidence_status"] == "tacit"
    pump(world)
    review.approve_hint(world, RANA, hid)
    pump(world)
    assert world.search.get("notes", hid)["evidence_status"] == "tacit" and world.search.get("notes", hid)["acl_groups"] == [FIN_READERS]


def test_evidence_is_validated_on_the_server_and_the_author_comes_from_the_token(world):
    cid = chat_api.suggest_evidence(world, SARA, "Jebel Ali warehouse")[0]["chunk_id"]
    world.ops.change_dossier_acl(TREASURY, [FIN_TREASURY], "R. Saleh", "Treasury only")
    pump(world)
    treasury_chunk = chat_api.suggest_evidence(world, SARA, "hedge loss revised schedule")[0]["chunk_id"]
    with pytest.raises(chat_api.HintError, match="scope"):  # Omar is an expert but is not in the treasury group
        submit(world, OMAR, evidence=[{"chunk_id": treasury_chunk, "lines": ["p001/L8"]}])
    with pytest.raises(chat_api.HintError, match="scope"):  # a chunk that does not exist
        submit(world, evidence=[{"chunk_id": "FIN-C03-S2-F0117-r1-D09__v1__c0001", "lines": []}])
    with pytest.raises(chat_api.HintError, match="not in"):
        submit(world, evidence=[{"chunk_id": cid, "lines": ["p999/L1"]}])
    with pytest.raises(PermissionError):
        submit(world, LAYLA)  # a reader cannot submit hints
    with pytest.raises(chat_api.HintError):
        submit(world, type=HintType.terminology, terms=["only one"])
    unregistered = Principal("e", "Outsider", ["DocAI.Expert"], ["not-a-registered-group"])
    with pytest.raises(PermissionError):
        submit(world, unregistered)
    hid = submit(world, evidence=[{"chunk_id": cid, "lines": ["p001/L1"]}])
    h = world.ops.get_hint(hid)
    assert h["author_oid"] == SARA.oid and h["author_name"] == "Sara Aziz"


def test_a_note_resting_on_a_restricted_dossier_is_visible_only_to_that_dossiers_readers(world):
    world.ops.change_dossier_acl(TREASURY, [FIN_TREASURY], "R. Saleh", "Treasury only")
    pump(world)
    cid = chat_api.suggest_evidence(world, SARA, "hedge loss revised schedule")[0]["chunk_id"]
    assert cid.startswith("FIN-C07")
    hid = submit(world, text="The 2009 hedge loss was reported again in the revised schedule.", evidence=[{"chunk_id": cid, "lines": ["p001/L8"]}])
    pump(world)
    review.approve_hint(world, RANA, hid)
    pump(world)
    assert world.search.get("notes", hid)["acl_groups"] == [FIN_TREASURY], "a department-wide note must not expose restricted content"


def test_a_steward_can_widen_a_note_only_with_a_reason_and_it_is_audited(world):
    world.ops.change_dossier_acl(TREASURY, [FIN_TREASURY], "R. Saleh", "Treasury only")
    pump(world)
    cid = chat_api.suggest_evidence(world, SARA, "hedge loss revised schedule")[0]["chunk_id"]
    hid = submit(world, text="Hedge losses are reviewed each January.", evidence=[{"chunk_id": cid, "lines": ["p001/L8"]}])
    pump(world)
    with pytest.raises(review.ReviewError):
        review.approve_hint(world, RANA, hid, widen_to=[FIN_READERS])
    review.approve_hint(world, RANA, hid, widen_to=[FIN_READERS], widen_reason="The policy itself is not confidential")
    pump(world)
    assert world.search.get("notes", hid)["acl_groups"] == [FIN_READERS]
    audit = world.ops.debug_rows("acl_audit", hint_id=hid)[0]
    assert audit["widened"] == 1 and "not confidential" in audit["reason"]


def test_restricting_a_dossier_updates_notes_anchored_to_it_and_tells_the_author(world):
    hid = submit(world, text="The 2008 hedge loss in this dossier was AED 4.2M; see the revised schedule on p.31.",
                 scope_dossier_ids=[TREASURY], evidence=evidence_for(world, SARA, "hedge loss"))
    pump(world)
    review.approve_hint(world, RANA, hid)
    pump(world)
    assert world.search.get("notes", hid)["acl_groups"] == [FIN_READERS]
    world.ops.change_dossier_acl(TREASURY, [FIN_TREASURY], "R. Saleh", "Treasury only per policy TR-04")
    pump(world)
    assert world.search.get("notes", hid)["acl_groups"] == [FIN_TREASURY]
    assert world.ops.get_hint(hid)["status"] == "published", "the history shows no approval that a person did not make"
    titles = [r["title"] for r in world.ops.inbox_for(SARA.oid, [], False)]
    assert any("Access to your note" in t for t in titles)


def test_rejection_needs_a_reason_the_author_is_told_and_nothing_is_indexed(world):
    hid = submit(world)
    pump(world)
    with pytest.raises(review.ReviewError):
        review.reject_hint(world, RANA, hid, "  ")
    review.reject_hint(world, RANA, hid, "Already covered by hint-000512")
    pump(world)
    assert world.search.get("notes", hid) is None and world.ops.get_hint(hid)["status"] == "rejected"
    row = world.ops.inbox_for(SARA.oid, [], False)[0]
    assert "not accepted" in row["title"] and "hint-000512" in row["body"]


def test_revoking_removes_the_note_and_the_synonyms_and_only_a_steward_may(world):
    note = submit(world)
    term = submit(world, type=HintType.terminology, text="Project Falcon names", terms=["Project Falcon", "Jebel Ali warehouse expansion", "مشروع الصقر"])
    pump(world)
    for h in (note, term):
        review.approve_hint(world, RANA, h)
    pump(world)
    assert any("Project Falcon" in r for r in world.search.synonym_map("en-synonyms")) and any("مشروع الصقر" in r for r in world.search.synonym_map("ar-synonyms"))
    assert any("aed, dirham" in r for r in world.search.synonym_map("en-synonyms")), "the seed rules stay"
    with pytest.raises(PermissionError):
        review.revoke_hint(world, SARA, note, "no")
    review.revoke_hint(world, RANA, note, "Cost centre 4410 also covered a second project")
    review.revoke_hint(world, RANA, term, "wrong names")
    pump(world)
    assert world.search.get("notes", note) is None
    assert not any("Project Falcon" in r for r in world.search.synonym_map("en-synonyms"))
    assert world.ops.get_hint(note)["status"] == "revoked"
    assert any("was revoked" in r["title"] for r in world.ops.inbox_for(SARA.oid, [], False))


def test_a_stale_message_is_completed_without_action(world):
    hid = submit(world)
    from docai.contracts.messages import Envelope
    from docai.modules import hint_worker
    h = world.ops.get_hint(hid)
    stale = Envelope(type="hint.changed", subject=hid, department="FIN", payload={"status": "submitted", "version": 1, "row_version": h["row_version"] - 1})
    hint_worker.handle(world, stale)
    assert world.ops.get_hint(hid)["status"] == "submitted"
    pump(world)
    review.edit_hint(world, RANA, hid, "Project Falcon, internal name 2006-2009, for the Jebel Ali expansion.")
    assert world.ops.get_hint(hid)["version"] == 2 and world.ops.get_hint(hid)["editor_name"] == "Rana Saleh"


def test_a_transcription_fix_goes_to_another_reviewer_and_records_its_outcome(world):
    line = f"{LEASE}@r1/p005/L1"  # a printed line a reader believes was misread
    fix = "Background. The warehouse supports the Jebel Ali distribution"
    hid = chat_api.submit_hint(world, SARA, department="FIN", type=HintType.transcription_fix, language="en", text="The first word is misread",
                               target_line_key=line, suggested_text=fix)
    pump(world)
    task = next(t for t in world.ops.list_tasks("FIN", "open") if t["hint_id"] == hid)
    assert task["reason"] == "expert_hint" and task["suggested_text"] == fix
    world.ops.record_demand([{"line_key": line, "kind": "blocked"}])
    assert review.claim_next(world, SARA.oid, ["FIN"])["task_id"] != task["task_id"], "nobody settles the task of their own hint"
    # Sara's claim above took another task; give it back by letting the lease lapse is not needed: Omar takes the fix
    mine = review.claim_next(world, OMAR.oid, ["FIN"])
    assert mine["task_id"] == task["task_id"]
    review.decide(world, task_id=mine["task_id"], lease_token=mine["lease_token"], user_oid=OMAR.oid, user_name="Omar", departments=["FIN"],
                  decision=Decision.correct, text=fix)
    pump(world)
    assert world.ops.get_hint(hid)["status"] == "published"
    new = LinesFile.model_validate_json(world.blobs.read("extracted", keys.PageRef(LEASE, 1, 5).dir + f"lines.v{world.ops.get_document(f'{LEASE}-r1-D03').current_version}.json"))
    assert new.line("L1").text == fix and new.line("L1").tier is TrustTier.human_verified
    assert any("approved" in r["title"] or "now used" in r["title"] for r in world.ops.inbox_for(SARA.oid, [], False))


def test_an_escalated_task_reaches_the_stewards_inbox_once(world):
    clock = FixedClock()
    world.ops.clock = clock
    world.ops.record_demand([{"line_key": world.ops.get_task(88412)["line_key"], "kind": "blocked"}])
    for _ in range(3):
        review.claim_next(world, OMAR.oid, ["FIN"])
        clock.advance(minutes=16)
    review.claim_next(world, SARA.oid, ["FIN"])
    review.claim_next(world, SARA.oid, ["FIN"])  # a second claim must not announce it again
    pump(world)
    rows = world.ops.inbox_for(RANA.oid, ["FIN"], False)
    assert [r["title"] for r in rows].count("Review task 88412 needs a steward") == 1
    assert world.ops.inbox_for(LAYLA.oid, [], False) == []


def test_the_notifier_does_not_duplicate_a_redelivered_event(world):
    hid = submit(world)
    pump(world)
    review.reject_hint(world, RANA, hid, "dup")
    pump(world)
    from docai.contracts.messages import Envelope
    from docai.modules import notifier
    env = Envelope(type="hint.rejected", subject=hid, department="FIN", payload={"hint_id": hid, "author_oid": SARA.oid, "reason": "dup"})
    notifier.handle(world, env)
    notifier.handle(world, env)
    assert sum(1 for r in world.ops.inbox_for(SARA.oid, [], False) if r["type"] == "hint.rejected" and r["event_id"].endswith(env.created_at.isoformat())) == 1
