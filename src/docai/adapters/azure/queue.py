"""Service Bus adapter of the Queue port (Entra authentication, no keys). Messages are received in peek-lock mode; the lock
is renewed while a handler works, and a delivery is settled on the receiver that produced it."""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from docai.contracts.messages import QUEUES, SUBSCRIPTION_NOTIFY, TOPIC, Envelope
from docai.ports import Delivery

log = logging.getLogger("docai.adapters.azure.queue")


def _body(m: Any) -> bytes | str:
    return m.body if isinstance(m.body, (bytes, str)) else b"".join(m.body)


class _Batch:
    """One receiver and the deliveries still waiting to be settled on it; the receiver closes with the last one."""

    def __init__(self, receiver: Any, renewer: Any, count: int) -> None:
        self.receiver, self.renewer, self.pending = receiver, renewer, count
        self.lock = threading.Lock()

    def settled(self) -> None:
        with self.lock:
            self.pending -= 1
            if self.pending == 0:
                self.renewer.close()
                self.receiver.close()


class ServiceBusQueue:
    def __init__(self, namespace: str, credential: Any = None, *, 
                client: Any = None, max_wait: float = 5.0, 
                max_lock_renewal: int = 1800) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.servicebus import ServiceBusClient

        self.namespace, self.cred = namespace, credential or DefaultAzureCredential()
        self.client = client or ServiceBusClient(namespace, self.cred)
        self.max_wait, self.max_lock_renewal = max_wait, max_lock_renewal
        self._senders: dict[str, Any] = {}
        self._lock = threading.Lock()

    def _sender(self, destination: str):
        with self._lock:
            if destination not in self._senders:
                self._senders[destination] = (self.client.get_topic_sender(destination) if destination == TOPIC else self.client.get_queue_sender(destination))
            return self._senders[destination]

    # sending
    def send(self, destination: str, envelope: Envelope, *, 
            message_id: str, session_id: str | None = None, 
            scheduled_at: datetime | None = None) -> bool:
        """Always True: Service Bus drops a duplicate MessageId silently, so the caller cannot be told."""
        from azure.servicebus import ServiceBusMessage

        if destination != TOPIC and destination not in QUEUES:
            raise ValueError(f"unknown queue {destination}")
        if destination in QUEUES and QUEUES[destination].sessions and not session_id:
            raise ValueError(f"{destination} is session-enabled: SessionId (the document ID) is required")
        props = {
            "type": envelope.type, 
            "department": envelope.department, 
            "priority": str(envelope.priority.value)
            }
        msg = ServiceBusMessage(envelope.to_json(), 
                                message_id=message_id, 
                                session_id=session_id, 
                                correlation_id=envelope.dossier_id, 
                                subject=envelope.type,
                                content_type="application/json", 
                                application_properties=props)  # `type` as a property lets the notify filter see it
        s = self._sender(destination)
        if scheduled_at is not None:
            s.schedule_messages(msg, scheduled_at)
        else:
            s.send_messages(msg)
        return True

    # receiving
    def _receiver(self, queue: str):
        from azure.servicebus import NEXT_AVAILABLE_SESSION

        if queue == SUBSCRIPTION_NOTIFY:
            return self.client.get_subscription_receiver(
                TOPIC, SUBSCRIPTION_NOTIFY, max_wait_time=self.max_wait
                )
        if QUEUES[queue].sessions:
            return self.client.get_queue_receiver(
                queue, session_id=NEXT_AVAILABLE_SESSION, 
                max_wait_time=self.max_wait
                )
        return self.client.get_queue_receiver(queue, max_wait_time=self.max_wait)

    def receive(self, queue: str, *, max_messages: int = 10) -> list[Delivery]:
        from azure.servicebus import AutoLockRenewer
        from azure.servicebus.exceptions import OperationTimeoutError, SessionCannotBeLockedError

        session_queue = queue != SUBSCRIPTION_NOTIFY and QUEUES[queue].sessions
        receiver = None
        try:  # the session link opens inside receive_messages, not in the constructor
            receiver = self._receiver(queue)
            msgs = receiver.receive_messages(max_message_count=max_messages, max_wait_time=self.max_wait)
        except (OperationTimeoutError, SessionCannotBeLockedError):
            if receiver is not None:
                receiver.close()
            if session_queue:  # no session has messages right now
                return []
            raise  # on a plain queue a timeout is a real fault
        good = []
        for m in msgs or []:
            try:
                good.append((m, Envelope.from_json(_body(m))))
            except (ValueError, TypeError) as e:  # pydantic ValidationError is a ValueError
                log.error("unparseable envelope in %s (%s): %s", queue, m.message_id, e)
                try:
                    receiver.dead_letter_message(m, reason="unparseable_envelope", error_description=str(e)[:1024])
                except Exception:  # a lost lock on one message must not end the pass
                    log.exception("could not dead-letter %s (%s)", m.message_id, queue)
        if not good:
            receiver.close()
            return []
        renewer = AutoLockRenewer(max_lock_renewal_duration=self.max_lock_renewal)
        if getattr(receiver, "session", None) is not None:  # a session receiver locks the session; its messages have no lock of their own (D52)
            renewer.register(receiver, receiver.session)
        else:
            for m, _ in good:
                renewer.register(receiver, m)
        batch = _Batch(receiver, renewer, len(good))  # the dead-lettered ones are not counted: they are already settled
        return [Delivery(env, str(m.message_id), queue, int(m.delivery_count or 1), getattr(m, "session_id", None), token=(batch, m))
                for m, env in good]

    @staticmethod
    def _settle(d: Delivery, op: str, **kw) -> None:
        batch, msg = d.token
        try:
            getattr(batch.receiver, op)(msg, **kw)
        finally:
            batch.settled()

    def complete(self, d: Delivery) -> None:
        self._settle(d, "complete_message")

    def abandon(self, d: Delivery) -> None:
        self._settle(d, "abandon_message")  # after the maximum delivery count Service Bus dead-letters it itself

    def dead_letter(self, d: Delivery, reason: str) -> None:
        self._settle(d, "dead_letter_message", reason=reason[:128], error_description=reason[:1024])

    def peek_dead_letters(self, queue: str) -> list[Delivery]:
        from azure.servicebus import ServiceBusSubQueue

        if queue == SUBSCRIPTION_NOTIFY or queue not in QUEUES:
            return []
        with self.client.get_queue_receiver(queue, sub_queue=ServiceBusSubQueue.DEAD_LETTER) as r:  # peek only: never receive
            out = []
            for m in r.peek_messages(max_message_count=250):
                try:
                    env = Envelope.from_json(_body(m))
                except (ValueError, TypeError):
                    continue
                out.append(Delivery(env, str(m.message_id), queue, int(m.delivery_count or 0), getattr(m, "session_id", None)))
            return out

    def depth(self, queue: str) -> int:
        from azure.servicebus.management import ServiceBusAdministrationClient

        admin = ServiceBusAdministrationClient(self.namespace, self.cred)
        return admin.get_queue_runtime_properties(queue).active_message_count
