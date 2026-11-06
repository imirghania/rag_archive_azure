"""The message queue port."""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from docai.contracts.messages import Envelope
from docai.schemas.rows import Delivery


class Queue(Protocol):
    def send(self, destination: str, envelope: Envelope, *, 
            message_id: str, session_id: str | None = None,
            scheduled_at: datetime | None = None) -> bool:
        """Returns False when the message was dropped as a duplicate (same MessageId inside the window)."""

    def receive(self, queue: str, *, max_messages: int = 10) -> list[Delivery]: ...
    def complete(self, d: Delivery) -> None: ...
    def abandon(self, d: Delivery) -> None: ...
    def dead_letter(self, d: Delivery, reason: str) -> None: ...
    def peek_dead_letters(self, queue: str) -> list[Delivery]: ...
    def depth(self, queue: str) -> int: ...
