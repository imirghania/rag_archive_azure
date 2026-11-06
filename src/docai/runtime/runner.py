"""Runs handlers over queues. In Azure each job container calls `run_job`; locally `drain` plays the part of KEDA."""
from __future__ import annotations

import importlib
import logging
from collections.abc import Callable

from docai.core import catalog
from docai.contracts.messages import Envelope
from .context import Context
from .messaging import DeadLetter

log = logging.getLogger("docai.runtime.runner")
Handler = Callable[[Context, Envelope], None]


def load_handlers() -> dict[str, Handler]:
    """queue -> handler for every module that exists. A missing module is skipped (the build is incremental)."""
    out: dict[str, Handler] = {}
    for c in catalog.COMPONENTS:
        source = c.consumes_queue or c.consumes_subscription  # a subscription is read like a queue
        if not source:
            continue
        try:
            mod = importlib.import_module(f"docai.modules.{c.module}")
        except ModuleNotFoundError as e:
            if e.name != f"docai.modules.{c.module}":
                raise
            continue
        out[source] = mod.handle
    return out


def _settle(d, queue: str, op: Callable, *args) -> None:
    """A lost message or session lock (the SDK's ServiceBusError, not importable in this layer) must not end the pass:
    the message comes back after the lock expires."""
    try:
        op(*args)
    except Exception:
        log.exception("could not settle %s (%s)", d.message_id, queue)


def process_queue(ctx: Context, queue: str, handler: Handler, *, max_messages: int = 10) -> int:
    """One execution: receive in peek-lock mode, handle, then complete; any error abandons the message for a retry."""
    n = 0
    for d in ctx.queue.receive(queue, max_messages=max_messages):
        try:
            handler(ctx, d.envelope)
        except DeadLetter as e:
            log.error("dead-lettering %s (%s): %s", d.message_id, queue, e.reason)
            _settle(d, queue, ctx.queue.dead_letter, d, e.reason)
        except Exception:  # noqa: BLE001 - the contract is: abandon, and the queue dead-letters after five tries
            log.exception("handler failed for %s (%s), delivery %d", d.message_id, queue, d.delivery_count)
            _settle(d, queue, ctx.queue.abandon, d)
        else:
            _settle(d, queue, ctx.queue.complete, d)
        n += 1
    return n


def drain(ctx: Context, handlers: dict[str, Handler] | None = None, 
        *, max_rounds: int = 500) -> int:
    handlers = handlers or load_handlers()
    total = 0
    for _ in range(max_rounds):
        moved = sum(process_queue(ctx, q, h) for q, h in handlers.items())
        total += moved
        if moved == 0:
            return total
    raise RuntimeError("drain did not settle: a message loop?")


def run_job(queue: str, handler: Handler, ctx: Context | None = None) -> int:
    from .context import new_context

    ctx = ctx or new_context()
    return process_queue(ctx, queue, handler)
