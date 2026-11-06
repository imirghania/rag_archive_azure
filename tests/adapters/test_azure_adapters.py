"""The Azure adapters against stubs that have the documented shape of each SDK. They prove the logic we own (what is sent, how
results are read, how errors map). They cannot prove the services accept it: that is what the first deployment is for."""
import json
from types import SimpleNamespace as NS

import httpx
import pytest

from docai.contracts.messages import Envelope
from docai.security.tokens import current_token


def env(t="page.ocr.requested", **kw):
    return Envelope(type=t, subject=kw.pop("subject", "FIN-C03-S2-F0117@r1/p001"), dossier_id="FIN-C03-S2-F0117", revision=1, department="FIN", payload={"page_no": 1})


# ------------------------------------------------------------------------------------------------ Service Bus
class FakeSender:
    def __init__(self): self.sent, self.scheduled = [], []
    def send_messages(self, m): self.sent.append(m)
    def schedule_messages(self, m, t): self.scheduled.append((m, t))


class FakeReceiver:
    def __init__(self, msgs): self.msgs, self.ops, self.closed = msgs, [], False
    def receive_messages(self, **kw): return self.msgs
    def complete_message(self, m): self.ops.append(("complete", m))
    def abandon_message(self, m): self.ops.append(("abandon", m))
    def dead_letter_message(self, m, **kw): self.ops.append(("dead", m, kw))
    def close(self): self.closed = True
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def peek_messages(self, **kw): return self.msgs


class FakeClient:
    def __init__(self, msgs=()): self.senders, self.msgs, self.receivers = {}, list(msgs), []
    def get_queue_sender(self, n): return self.senders.setdefault(n, FakeSender())
    def get_topic_sender(self, n): return self.senders.setdefault(n, FakeSender())
    def get_queue_receiver(self, n, **kw): self.receivers.append(FakeReceiver(self.msgs)); return self.receivers[-1]
    def get_subscription_receiver(self, t, s, **kw): self.receivers.append(FakeReceiver(self.msgs)); return self.receivers[-1]


def sb_message(e, mid="m1", count=1, session=None):
    return NS(body=iter([e.to_json().encode()]), message_id=mid, delivery_count=count, session_id=session)


@pytest.fixture
def sb(monkeypatch):
    import azure.servicebus as asb
    monkeypatch.setattr(asb, "AutoLockRenewer", lambda **kw: NS(register=lambda r, m: None, close=lambda: None))
    from docai.adapters.azure.queue import ServiceBusQueue
    c = FakeClient([sb_message(env())])
    return ServiceBusQueue("ns.servicebus.windows.net", object(), client=c), c


def test_send_sets_message_id_session_and_the_type_as_a_property(sb):
    q, c = sb
    q.send("q-chunk", env("document.chunk.requested"), message_id="chunk:D:v2", session_id="D")
    m = c.senders["q-chunk"].sent[0]
    assert (m.message_id, m.session_id, m.correlation_id) == ("chunk:D:v2", "D", "FIN-C03-S2-F0117")
    assert m.application_properties["type"] == "document.chunk.requested"  # the notify subscription filters on it
    with pytest.raises(ValueError, match="SessionId"):
        q.send("q-index", env("document.index.requested"), message_id="x")
    with pytest.raises(ValueError):
        q.send("q-nope", env(), message_id="x")


def test_scheduled_sends_use_scheduling_and_events_go_to_the_topic(sb):
    from datetime import UTC, datetime
    q, c = sb
    when = datetime(2026, 11, 5, 9, 1, tzinfo=UTC)
    q.send("q-upload-commit", env("upload.commit.requested"), message_id="upload:u:try2", scheduled_at=when)
    assert c.senders["q-upload-commit"].scheduled[0][1] == when and not c.senders["q-upload-commit"].sent
    q.send("t-docai-events", env("document.indexed"), message_id="indexed:D:v1")
    assert len(c.senders["t-docai-events"].sent) == 1


def test_receive_settles_on_the_receiver_that_produced_the_message_and_closes_it_after_the_last(sb):
    q, c = sb
    d = q.receive("q-ocr-online")
    assert len(d) == 1 and d[0].message_id == "m1" and d[0].envelope.type == "page.ocr.requested" and d[0].delivery_count == 1
    r = c.receivers[0]
    q.dead_letter(d[0], "scan_timeout")
    assert r.ops[0][0] == "dead" and r.ops[0][2]["reason"] == "scan_timeout" and r.closed


def test_a_session_receiver_renews_the_session_lock_and_a_plain_receiver_renews_each_message(monkeypatch):
    """The real AutoLockRenewer.register refuses a message of a session receiver (ValueError); that crashed job-chunk-embed (D52)."""
    import azure.servicebus as asb
    registered = []
    monkeypatch.setattr(asb, "AutoLockRenewer", lambda **kw: NS(register=lambda r, x: registered.append(x), close=lambda: None))
    from docai.adapters.azure.queue import ServiceBusQueue
    session = object()

    def client(with_session):
        msgs = [sb_message(env("document.chunk.requested"), "m1", session="D"), sb_message(env("document.chunk.requested"), "m2", session="D")]
        c = FakeClient(msgs)
        make = c.get_queue_receiver

        def get(n, **kw):
            r = make(n, **kw)
            r.session = session if with_session else None
            return r
        c.get_queue_receiver = get
        return c

    q = ServiceBusQueue("ns.servicebus.windows.net", object(), client=client(True))
    assert len(q.receive("q-chunk")) == 2 and registered == [session], "one registration: the session, not each message"
    registered.clear()
    q = ServiceBusQueue("ns.servicebus.windows.net", object(), client=client(False))
    assert len(q.receive("q-ocr-online")) == 2 and len(registered) == 2 and session not in registered


def test_receive_on_an_empty_queue_closes_the_receiver_and_returns_nothing(sb):
    q, c = sb
    c.msgs.clear()
    assert q.receive("q-ocr-online") == [] and c.receivers[0].closed


def _timing_out(sb):
    """A receiver whose receive_messages raises the SDK's own timeout (the session link opens there, not in the constructor)."""
    from azure.servicebus.exceptions import OperationTimeoutError
    q, c = sb

    def boom(self, **kw): raise OperationTimeoutError(message="Timed out waiting for the AMQP link to open NEXT_AVAILABLE_SESSION")
    c.get_queue_receiver = lambda n, **kw: c.receivers.append(FakeReceiver(c.msgs)) or setattr(c.receivers[-1], "receive_messages", lambda **k: boom(None)) or c.receivers[-1]
    return q, c


def test_an_empty_session_queue_times_out_in_receive_and_is_nothing_to_do(sb):
    q, c = _timing_out(sb)
    assert q.receive("q-chunk") == [] and c.receivers[0].closed


def test_a_timeout_on_a_plain_queue_is_a_real_fault(sb):
    from azure.servicebus.exceptions import OperationTimeoutError
    q, _ = _timing_out(sb)
    with pytest.raises(OperationTimeoutError):
        q.receive("q-ocr-online")


def test_a_session_that_cannot_be_locked_is_nothing_to_do(sb):
    from azure.servicebus.exceptions import SessionCannotBeLockedError
    q, c = sb
    get = c.get_queue_receiver

    def locked(n, **kw):
        r = get(n, **kw)
        r.receive_messages = lambda **k: (_ for _ in ()).throw(SessionCannotBeLockedError(message="locked"))
        return r
    c.get_queue_receiver = locked
    assert q.receive("q-chunk") == [] and c.receivers[0].closed


def test_an_unparseable_envelope_is_dead_lettered_and_the_others_are_returned(sb):
    q, c = sb
    c.msgs[:] = [NS(body=iter([b'{"not": "an envelope"']), message_id="bad", delivery_count=1, session_id=None), sb_message(env(), "good")]
    d = q.receive("q-ocr-online")
    r = c.receivers[0]
    assert [x.message_id for x in d] == ["good"]
    assert [(op[0], op[1].message_id, op[2]["reason"]) for op in r.ops] == [("dead", "bad", "unparseable_envelope")] and not r.closed
    q.complete(d[0])
    assert r.closed, "the receiver closes after the last delivery that is still waiting"


def test_a_batch_of_only_unparseable_envelopes_closes_the_receiver(sb):
    q, c = sb
    c.msgs[:] = [NS(body=iter([b"nope"]), message_id="bad", delivery_count=1, session_id=None)]
    assert q.receive("q-ocr-online") == [] and c.receivers[0].closed and c.receivers[0].ops[0][0] == "dead"


def test_peek_dead_letters_skips_an_unparseable_envelope(sb):
    q, c = sb
    c.msgs.insert(0, NS(body=iter([b"nope"]), message_id="bad", delivery_count=1, session_id=None))
    assert [d.message_id for d in q.peek_dead_letters("q-ocr-online")] == ["m1"]


def test_the_notify_subscription_is_read_like_a_queue(sb):
    q, c = sb
    assert q.receive("notify")[0].queue == "notify"


def test_dead_letters_are_peeked_never_received(sb):
    q, c = sb
    assert [d.message_id for d in q.peek_dead_letters("q-ocr-online")] == ["m1"] and q.peek_dead_letters("notify") == []


# ------------------------------------------------------------------------------------------------ blobs
def test_blob_store_maps_azure_errors_and_block_ids(monkeypatch):
    from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
    from docai.adapters.azure.blobs import AdlsBlobStore, _block_id
    from docai.ports import AlreadyExists
    from docai.core.settings import Settings

    class Blob:
        def __init__(self): self.log, self.exists_ = [], True; self.url = "https://x/raw/a"
        def upload_blob(self, data, overwrite):
            self.log.append(("upload", overwrite))
            if not overwrite:
                raise ResourceExistsError("exists")
        def download_blob(self): raise ResourceNotFoundError("nope")
        def get_blob_tags(self): return self.tags
        def stage_block(self, bid, data): self.log.append(("block", bid))
        def get_block_list(self, kind): return [], [NS(id=_block_id(1)), NS(id=_block_id(0))]
    b = Blob()
    svc = NS(get_blob_client=lambda c, p: b)
    s = AdlsBlobStore(Settings(_env_file=None), object(), services={"raw": svc, "proc": svc, "staging": svc})
    with pytest.raises(AlreadyExists):
        s.write("raw", "a", b"x")
    s.write("extracted", "a", b"x", overwrite=True)
    with pytest.raises(FileNotFoundError):
        s.read("raw", "a")
    s.write_block("staging", "u/a", 7, b"x")
    assert b.log[-1] == ("block", _block_id(7)) and s.list_blocks("staging", "u/a") == [0, 1]
    for tags, want in (({}, "pending"), ({"Malware Scanning scan result": "No threats found"}, "clean"), ({"Malware Scanning scan result": "Malicious"}, "malicious")):
        b.tags = tags
        assert s.scan_result("staging", "u/a") == want


# ------------------------------------------------------------------------------------------------ OCR
def test_document_intelligence_result_becomes_our_ocr_contract():
    """Built from the SDK's own models: hand-made fakes once gave a word `spans`, the real DocumentWord has one `span` (D51)."""
    from azure.ai.documentintelligence.models import (
        AnalyzeResult, DocumentLine, DocumentPage, DocumentSpan, DocumentStyle, DocumentWord)

    from docai.adapters.azure.ocr import to_ocr_result
    span = lambda o, n: DocumentSpan(offset=o, length=n)  # noqa: E731
    poly = lambda y: [1.0, y, 3.0, y, 3.0, y + 0.3, 1.0, y + 0.3]  # noqa: E731
    word = lambda conf, o, n: DocumentWord(content="w", polygon=poly(2.0), span=span(o, n), confidence=conf)  # noqa: E731
    page = DocumentPage(page_number=1, width=8.27, height=11.69, unit="inch",
                        lines=[DocumentLine(content="Approved, pay 1,750", polygon=poly(2.0), spans=[span(0, 19)]),
                               DocumentLine(content="يرجى المتابعة", polygon=poly(3.0), spans=[span(20, 13)])],
                        words=[word(0.9, 0, 8), word(0.5, 9, 3), word(0.4, 20, 5)])
    res = AnalyzeResult(api_version="2024-11-30", model_id="prebuilt-layout", content="x", pages=[page],
                        styles=[DocumentStyle(is_handwritten=True, spans=[span(0, 19)])])
    out = to_ocr_result(res, 2480, 3508, from_text_layer=False)
    a, b = out.lines
    assert (a.id, a.style, a.conf) == ("L1", "handwritten", 0.7) and b.style == "printed" and b.lang == "ar"
    assert a.box.x0 == round(1.0 * 2480 / 8.27) and a.box.y1 == round(2.3 * 3508 / 11.69), "inches are converted to pixels of the 300 dpi image"
    assert to_ocr_result(res, 2480, 3508, from_text_layer=True).lines[0].from_text_layer is True


def test_the_ocr_adapter_sends_the_pdf_for_a_text_layer_page_and_the_image_otherwise():
    import io
    from PIL import Image
    from docai.adapters.azure.ocr import DocumentIntelligenceOcr
    seen = []
    page = NS(width=100, height=100, lines=[], words=[])
    client = NS(begin_analyze_document=lambda model, body: (seen.append((model, body.bytes_source)), NS(result=lambda: NS(pages=[page], styles=[])))[1])
    buf = io.BytesIO(); Image.new("L", (100, 100)).save(buf, "PNG")
    o = DocumentIntelligenceOcr("https://x", object(), client=client)
    o.read(buf.getvalue(), page_key="k")
    o.read(buf.getvalue(), page_key="k", text_layer_pdf=b"%PDF-")
    assert seen[0] == ("prebuilt-layout", buf.getvalue()) and seen[1] == ("prebuilt-layout", b"%PDF-")


# ------------------------------------------------------------------------------------------------ models
def parse_client(parsed=None, refusal=None):
    calls = []
    def parse(**kw):
        calls.append(kw)
        return NS(choices=[NS(message=NS(parsed=parsed, refusal=refusal, content=None))])
    return NS(beta=NS(chat=NS(completions=NS(parse=parse)))), calls


def test_chat_roles_use_their_own_deployment_and_a_refusal_is_an_error():
    from docai.adapters.azure.models import FoundryChat
    from docai.contracts.llm import VerifierOutput
    from docai.core.settings import Settings
    s = Settings(_env_file=None, models={"verifier": "gpt-5-mini", "router": "gpt-4o"})
    client, calls = parse_client(VerifierOutput(verdicts=[]))
    FoundryChat(s, client).complete_json("router", "sys", "usr", VerifierOutput)
    assert calls[0]["model"] == "gpt-4o" and calls[0]["response_format"] is VerifierOutput and calls[0]["messages"][0] == {"role": "system", "content": "sys"}
    bad, _ = parse_client(None, refusal="no")
    with pytest.raises(ValueError, match="no valid"):
        FoundryChat(s, bad).complete_json("verifier", "s", "u", VerifierOutput)


def test_the_second_reader_gets_the_crop_and_the_language_hint_and_nothing_else():
    from docai.adapters.azure.models import FoundryVision
    from docai.contracts.llm import VlmOutput
    from docai.core.settings import Settings
    client, calls = parse_client(VlmOutput(text="x"))
    FoundryVision(Settings(_env_file=None), client).transcribe(b"\x89PNGdata", lang_hint="ar", line_key="FIN-C03-S2-F0117@r1/p005/L11")
    msgs = calls[0]["messages"]
    assert calls[0]["model"] == "gpt-5-mini" and "`ar`" in msgs[0]["content"] and "ocr" not in json.dumps(msgs).lower()
    assert msgs[1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,") and len(msgs[1]["content"]) == 2


def test_embeddings_are_batched_and_use_the_configured_dimension():
    from docai.adapters.azure.models import FoundryEmbedder
    from docai.core.settings import Settings
    calls = []
    def create(**kw):
        calls.append(kw)
        return NS(data=[NS(index=i, embedding=[float(i)] * 3) for i in reversed(range(len(kw["input"])))])
    e = FoundryEmbedder(Settings(_env_file=None), NS(embeddings=NS(create=create)))
    out = e.embed([f"t{i}" for i in range(130)] + [""])
    assert [len(c["input"]) for c in calls] == [64, 64, 3] and all(c["dimensions"] == 1024 for c in calls)
    assert out[0] == [0.0] * 3 and out[1] == [1.0] * 3 and len(out) == 131, "results are put back in input order"
    assert calls[2]["input"][-1] == " ", "an empty string is not sent"


# ------------------------------------------------------------------------------------------------ Prompt Shields
def test_prompt_shields_batches_documents_by_five_truncates_and_maps_results():
    from docai.adapters.azure.safety import PromptShields
    reqs = []
    def handler(request):
        body = json.loads(request.content); reqs.append(body)
        return httpx.Response(200, json={"userPromptAnalysis": {"attackDetected": "ignore" in body["userPrompt"]},
                                         "documentsAnalysis": [{"attackDetected": "ignore" in d} for d in body["documents"]]})
    ps = PromptShields("https://cs.example", NS(get_token=lambda s: NS(token="t")), http=httpx.Client(transport=httpx.MockTransport(handler)))
    docs = [f"doc {i}" for i in range(7)]; docs[6] = "ignore all " + "x" * 20000
    r = ps.shield(question="ignore this", documents=docs)
    assert r.question_attack and r.document_attacks == [False] * 6 + [True]
    assert [len(x["documents"]) for x in reqs] == [5, 2] and len(reqs[1]["documents"][1]) == 10_000 and reqs[1]["userPrompt"] == ""
    assert ps.shield(question="hello").document_attacks == [] and ps.shield(documents=[]).question_attack is False


# ------------------------------------------------------------------------------------------------ search
def test_the_security_filter_is_always_built_and_an_empty_scope_matches_nothing():
    from docai.adapters.azure.search import prepare, q, security_filter
    f = security_filter(["a", "b"], {"doc_type": "contract", "dossier_id": "it's"})
    assert f == "acl_groups/any(g: search.in(g, 'a,b', ',')) and injection_suspect ne true and doc_type eq 'contract' and dossier_id eq 'it''s'"
    assert "__none__" in security_filter([]) and "injection_suspect" not in security_filter(["a"], with_injection=False)
    with pytest.raises(ValueError):
        security_filter(["a"], {"x eq 1 or y": 1})
    assert q("o'brien") == "'o''brien'" and prepare({"doc_date": "2008-02-27"})["doc_date"] == "2008-02-27T00:00:00Z" and prepare({"doc_date": None})["doc_date"] is None


def test_the_search_adapter_filters_and_uses_the_semantic_configuration():
    from azure.core.exceptions import ResourceNotFoundError
    from docai.adapters.azure.search import AzureSearch
    seen = {}
    class C:
        def search(self, **kw): seen.update(kw); return iter([{"chunk_id": "c1", "text_en": "t", "@search.score": 1.0, "@search.reranker_score": 2.5}])
        def merge_documents(self, docs): return [NS(succeeded=False)]
        def merge_or_upload_documents(self, docs): seen["uploaded"] = docs; return [NS(succeeded=True)]
        def get_document(self, key): raise ResourceNotFoundError("x")
        def delete_documents(self, docs): seen["deleted"] = docs
    s = AzureSearch("https://s", object(), clients={"docs": C()})
    hit = s.search("docs", text="lease", vector=[0.1, 0.2], acl_groups=["g1"], top=3, filters={"dossier_id": "D"})[0]
    assert hit.id == "c1" and hit.score == 2.5 and "@search.score" not in hit.doc
    assert seen["semantic_configuration_name"] == "docs-semantic" and seen["query_type"] == "semantic" and seen["top"] == 3
    assert "search.in(g, 'g1', ',')" in seen["filter"] and "dossier_id eq 'D'" in seen["filter"] and seen["vector_queries"][0].fields == "text_vector"
    seen.clear()
    assert s.search("docs", text="x", vector=[], acl_groups=["g"]) and "vector_queries" not in seen, "no vector: a keyword-only query"
    assert s.merge("docs", {"chunk_id": "c9"}) is False and s.get("docs", "c9") is None
    s.upload("docs", [{"chunk_id": "c1", "doc_date": "2008-02-27"}])
    assert seen["uploaded"][0]["doc_date"].endswith("Z")
    s.delete("docs", ["c1"]); assert seen["deleted"] == [{"chunk_id": "c1"}]
    s.ids("docs", document_id="D", version_lt=3, injection_suspect=False)
    assert seen["filter"] == "document_id eq 'D' and version lt 3 and injection_suspect eq false"


# ------------------------------------------------------------------------------------------------ Foundry agent
class Resp:
    def __init__(self, i, output=(), text=""): self.id, self.output, self.output_text = i, list(output), text


def test_the_agent_loop_runs_tools_with_the_callers_executor_and_deletes_every_response():
    from docai.adapters.azure.agent import FoundryAnswerAgent
    deleted, created = [], []
    script = iter([Resp("r1", [NS(type="function_call", name="search_documents", arguments='{"query": "rent"}', call_id="c1")]),
                   Resp("r2", [NS(type="function_call", name="search_notes", arguments="{}", call_id="c2")]),
                   Resp("r3", [], "The rent is 1,750 [c:X#p1/L1].")])
    client = NS(responses=NS(create=lambda **kw: (created.append(kw), next(script))[1], delete=lambda i: deleted.append(i)))
    calls = []
    def tools(call):
        calls.append(call)
        if call.name == "search_notes":
            raise RuntimeError("index down")
        return '[{"chunk_id": "X"}]'
    out = FoundryAnswerAgent(NS(azure=NS(foundry_project_endpoint="x")), openai_client=client).run(
        question="How much?", queries={"en": "rent", "ar": ""}, history=[{"question": "q0", "answer": "a0"}], tools=tools, correction="Claim 1 failed")
    assert out == "The rent is 1,750 [c:X#p1/L1]." and [c.name for c in calls] == ["search_documents", "search_notes"] and calls[0].arguments == {"query": "rent"}
    assert deleted == ["r1", "r2", "r3"], "nothing stays in the service after the answer"
    first = created[0]
    assert first["extra_body"]["agent_reference"] == {"name": "docai-answer-agent", "type": "agent_reference"}
    assert [m["role"] for m in first["input"]] == ["user", "assistant", "user"] and "Correction needed: Claim 1 failed" in first["input"][-1]["content"]
    assert created[1]["previous_response_id"] == "r1" and json.loads(created[2]["input"][0]["output"]) == {"error": "index down"}, "a failed tool is reported to the agent"


def test_an_agent_that_never_stops_calling_tools_ends_as_no_evidence():
    from docai.adapters.azure.agent import FoundryAnswerAgent
    n = iter(range(100))
    client = NS(responses=NS(create=lambda **kw: Resp(f"r{next(n)}", [NS(type="function_call", name="search_documents", arguments="{}", call_id="c")]), delete=lambda i: None))
    out = FoundryAnswerAgent(NS(azure=NS(foundry_project_endpoint="x")), openai_client=client).run(question="q", queries={}, history=[], tools=lambda c: "[]")
    assert out.startswith("NO_EVIDENCE")


def test_ensure_agent_creates_a_version_only_when_the_definition_changed():
    from docai.adapters.azure.agent import definition_hash, ensure_agent
    from docai.core.settings import Settings
    s = Settings(_env_file=None)
    created = []
    state = {"meta": None}
    project = NS(agents=NS(get=lambda agent_name: NS(metadata=state["meta"]) if state["meta"] else (_ for _ in ()).throw(RuntimeError("404")),
                           create_version=lambda **kw: (created.append(kw), state.update(meta=kw["metadata"]))))
    assert ensure_agent(project, s) == definition_hash(s) and len(created) == 1
    ensure_agent(project, s)
    assert len(created) == 1, "same model, instructions and tools: no new version"
    s2 = Settings(_env_file=None, models={"answer_agent": "gpt-5"})
    ensure_agent(project, s2)
    assert len(created) == 2 and created[1]["definition"].model == "gpt-5"
    assert {t.name for t in created[1]["definition"].tools} == {"search_documents", "search_notes"}


# ------------------------------------------------------------------------------------------------ HTTP clients and context
def test_the_http_clients_forward_the_callers_token_and_refuse_to_run_without_one():
    from docai.adapters.azure.services import HttpRetrieval, HttpVerifier
    seen = []
    def handler(request):
        seen.append((request.url.path, request.headers.get("authorization"), json.loads(request.content)))
        return httpx.Response(200, json=[{"chunk_id": "c"}] if "search" in request.url.path else {"claims": [{"claim_id": 1, "text": "t", "citations": [], "verdict": "supported"}], "blocked_lines": ["l"], "ok": True})
    http = httpx.Client(base_url="http://x", transport=httpx.MockTransport(handler))
    r, v = HttpRetrieval("http://x", http), HttpVerifier("http://x", http)
    with pytest.raises(RuntimeError, match="no user token"):
        r.search_documents(scope=["g"], query="q")
    t = current_token.set("tok-1")
    try:
        assert r.search_documents(scope=["IGNORED"], query="q", top=3)[0]["chunk_id"] == "c"
        verdict = v.verify(draft="d", evidence={}, scope=["IGNORED"])
    finally:
        current_token.reset(t)
    assert seen[0] == ("/search/documents", "Bearer tok-1", {"query": "q", "language": "en", "top": 3, "filters": None})
    assert "IGNORED" not in json.dumps(seen), "the scope never travels: the server derives it from the token"
    assert verdict.ok and verdict.blocked_lines == ["l"]


def test_the_azure_context_builds_without_touching_azure_and_uses_the_database_setting_for_ops(monkeypatch):
    from docai.app.wiring import build_context
    from docai.core.settings import Settings
    s = Settings(_env_file=None, adapters="azure", azure={"servicebus_namespace": "ns.servicebus.windows.net", "storage_raw_account": "r", "storage_proc_account": "p",
                 "storage_staging_account": "s", "search_endpoint": "https://s", "foundry_endpoint": "https://f",
                 "foundry_project_endpoint": "https://f/api/projects/p", "ocr_endpoint": "https://o", "content_safety_endpoint": "https://c"},
                 auth={"tenant_id": "t", "api_client_id": "c"}, database={"url": "postgresql+psycopg://u:p@pg.example:5432/docai"})
    ctx = build_context(s)
    assert type(ctx.queue).__name__ == "ServiceBusQueue" and type(ctx.ops).__name__ == "SqlOps" and ctx.ops.engine.url.host == "pg.example" and type(ctx.agent).__name__ == "FoundryAnswerAgent"
    assert type(ctx.identity).__name__ == "EntraIdentity" and type(ctx.search).__name__ == "AzureSearch"
    s.ocr_engine = "content_understanding"
    with pytest.raises(NotImplementedError):
        build_context(s)


def test_the_converter_only_accepts_word_and_text():
    from docai.adapters.azure.convert import LibreOfficeConverter
    with pytest.raises(ValueError):
        LibreOfficeConverter("soffice").to_pdf(b"x", "a.xlsx")


def test_the_real_client_is_opened_on_the_versioned_index_name(monkeypatch):
    """Aliases cannot be queried with the stable API version, so `docs` and `notes` are the indexes docs-v1 and notes-v1."""
    opened: list[str] = []

    class FakeClient:
        def __init__(self, endpoint, index, credential):
            opened.append(index)

    monkeypatch.setattr("azure.search.documents.SearchClient", FakeClient)
    from docai.adapters.azure.search import AzureSearch

    s = AzureSearch("https://x.search.windows.net", credential=object())
    s._c("docs"), s._c("notes")
    assert opened == ["docs-v1", "notes-v1"]
