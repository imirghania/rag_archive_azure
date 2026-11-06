from types import SimpleNamespace as NS

from azure.servicebus.exceptions import MessageLockLostError

from docai.contracts.messages import Envelope
from docai.ports import Delivery
from docai.runtime.runner import process_queue


def _delivery(mid):
    e = Envelope(type="page.ocr.requested", subject=mid, dossier_id="FIN-C03-S2-F0117", revision=1, department="FIN", payload={"page_no": 1})
    return Delivery(e, mid, "q-ocr-online", 1, None)


class LosingQueue:
    def __init__(self, ds): self.ds, self.completed = ds, []
    def receive(self, queue, *, max_messages=10): return self.ds
    def complete(self, d):
        if d.message_id == "m1":
            raise MessageLockLostError(message="lock lost")
        self.completed.append(d.message_id)


def test_a_lost_lock_when_settling_does_not_stop_the_batch(caplog):
    seen, q = [], LosingQueue([_delivery("m1"), _delivery("m2")])
    n = process_queue(NS(queue=q), "q-ocr-online", lambda ctx, env: seen.append(env.subject))
    assert n == 2 and seen == ["m1", "m2"] and q.completed == ["m2"]
    assert any("m1" in r.getMessage() and r.name == "docai.runtime.runner" for r in caplog.records)
