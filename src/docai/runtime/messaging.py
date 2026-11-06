"""Building and sending envelopes. Shared by every module (it is a library, not a module)."""
from __future__ import annotations

from typing import Any

from docai.contracts import keys
from docai.contracts.messages import ROUTES, Envelope, destination_of, session_of

from .context import Context


class DeadLetter(Exception):
    """Raised by a handler that must not be retried: the runner dead-letters the message with this reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def envelope(msg_type: str, subject: str, *, 
            department: str, dossier_id: str | None = None, revision: int | None = None,
            payload: dict[str, Any] | None = None, priority: str = "online") -> Envelope:
    return Envelope(type=msg_type, subject=subject, 
                    dossier_id=dossier_id, revision=revision, 
                    department=department, priority=priority, 
                    payload=payload or {})  # type: ignore[arg-type]


def send(ctx: Context, env: Envelope, *, 
        message_id: str, document_id: str | None = None) -> bool:
    dest = destination_of(env.type)
    return ctx.queue.send(dest, env, message_id=message_id, 
                        session_id=session_of(dest, document_id),
                        scheduled_at=None)


def revision_of(env: Envelope) -> tuple[str, int]:
    """The dossier ID and revision of any dossier-level or page-level message."""
    if env.dossier_id and env.revision:
        return env.dossier_id, env.revision
    base = env.subject.split("/")[0]
    return keys.parse_dossier_key(base)


__all__ = ["ROUTES", "DeadLetter", "envelope", "revision_of", "send"]
