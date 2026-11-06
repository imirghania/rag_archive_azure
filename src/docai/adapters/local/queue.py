"""In-memory queue with the Service Bus behaviours the design relies on: peek-lock, delivery count and dead-letter after
five attempts, duplicate detection by MessageId, sessions (one session at a time, in order), scheduled messages, and the
topic with its `notify` subscription filter."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from docai.contracts.messages import (
    NOTIFY_TYPES,
    QUEUES,
    SUBSCRIPTION_NOTIFY,
    TOPIC,
    Envelope,
)
from docai.ports import Delivery

MAX_DELIVERY = 5


@dataclass
class _Msg:
    envelope: Envelope
    message_id: str
    session_id: str | None
    deliveries: int = 0
    locked: bool = False
    available_at: datetime | None = None
    dead_reason: str | None = None


@dataclass
class _Entity:
    live: list[_Msg] = field(default_factory=list)
    dead: list[_Msg] = field(default_factory=list)
    seen_ids: set[str] = field(default_factory=set)


class LocalQueue:
    def __init__(self, clock=None) -> None:
        self._clock = clock
        self._entities: dict[str, _Entity] = {}
        self.sent_log: list[tuple[str, str, str]] = []  # (destination, type, message_id), for tests

    def _ent(self, name: str) -> _Entity:
        return self._entities.setdefault(name, _Entity())

    # sending
    def send(self, destination: str, envelope: Envelope, *, 
            message_id: str, session_id: str | None = None,
            scheduled_at: datetime | None = None) -> bool:
        if destination == TOPIC:  # the topic fans out to subscriptions by filter
            self.sent_log.append((destination, envelope.type, message_id))
            if envelope.type in NOTIFY_TYPES:
                return self._enqueue(SUBSCRIPTION_NOTIFY, envelope, message_id, None, None)
            return True
        if destination not in QUEUES:
            raise ValueError(f"unknown queue {destination}")
        spec = QUEUES[destination]
        if spec.sessions and not session_id:
            raise ValueError(f"{destination} is session-enabled: SessionId (the document ID) is required")
        self.sent_log.append((destination, envelope.type, message_id))
        return self._enqueue(destination, envelope, message_id, session_id, scheduled_at)

    def _enqueue(self, name: str, env: Envelope, message_id: str, session_id: str | None, scheduled_at) -> bool:
        ent = self._ent(name)
        if message_id in ent.seen_ids:
            return False
        ent.seen_ids.add(message_id)
        ent.live.append(_Msg(env, message_id, session_id, available_at=scheduled_at))
        return True

    def forget_duplicate_window(self, queue: str) -> None:
        """Simulates the detection window ending (a re-sent message with an old ID is then accepted)."""
        self._ent(queue).seen_ids.clear()

    # receiving
    def receive(self, queue: str, *, max_messages: int = 10) -> list[Delivery]:
        ent = self._ent(queue)
        now = self._clock.now() if self._clock else None
        ready = [m for m in ent.live if 
                not m.locked and (
                    m.available_at is None or now is None or m.available_at <= now
                    ) ]
        if not ready:
            return []
        if QUEUES.get(queue) and QUEUES[queue].sessions:
            locked_sessions = {m.session_id for m in ent.live if m.locked}
            ready = [m for m in ready if m.session_id not in locked_sessions]
            if not ready:
                return []
            first = ready[0].session_id  # one session at a time, messages in the order they were sent
            ready = [m for m in ready if m.session_id == first]
        out = []
        for m in ready[:max_messages]:
            m.locked = True
            m.deliveries += 1
            out.append(Delivery(m.envelope, m.message_id, queue,
                                m.deliveries, m.session_id, token=m))
        return out

    def complete(self, d: Delivery) -> None:
        self._ent(d.queue).live.remove(d.token)

    def abandon(self, d: Delivery) -> None:
        m: _Msg = d.token
        m.locked = False
        if m.deliveries >= MAX_DELIVERY:
            self.dead_letter(d, "MaxDeliveryCountExceeded")

    def dead_letter(self, d: Delivery, reason: str) -> None:
        ent = self._ent(d.queue)
        m: _Msg = d.token
        if m in ent.live:
            ent.live.remove(m)
        m.dead_reason, m.locked = reason, False
        ent.dead.append(m)

    def peek_dead_letters(self, queue: str) -> list[Delivery]:
        return [Delivery(m.envelope, m.message_id, queue, 
                        m.deliveries, m.session_id, token=m) 
                for m in self._ent(queue).dead]

    def depth(self, queue: str) -> int:
        return len(self._ent(queue).live)

    def total_depth(self) -> int:
        return sum(len(e.live) for e in self._entities.values())
