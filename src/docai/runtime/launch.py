"""What runs when a container starts: `python -m docai.modules.<name>` ends in one of these (spec, Container Apps catalog).

* queue_job:       an event-driven job execution. Handles messages until the queue is empty, then exits.
* scheduled:       a scheduled job execution (the watchdog): one pass, then exit.
* queue_consumer:  an app that scales on a queue or subscription and keeps reading while it runs.
* http_app:        an HTTP app served by uvicorn on port 8000.
* web_app:         app-web, which gets its app factory and sign-in flow from modules.web."""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Callable
from typing import Any

from .context import Context, new_context
from .runner import Handler, process_queue

log = logging.getLogger("docai.runtime.launch")


class JsonFormatter(logging.Formatter):
    """One record, one valid JSON line: quotes and tracebacks are escaped by json.dumps."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        return json.dumps({"time": self.formatTime(record), "level": record.levelname, "logger": record.name, "message": message})


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=os.environ.get("DOCAI_LOG_LEVEL", "INFO"), handlers=[handler])
    for noisy in ("azure", "httpx2", "httpx", "uvicorn.access"):  # the SDK logs every request with all headers at INFO; Log Analytics bills per GB
        logging.getLogger(noisy).setLevel(logging.WARNING)
    conn = os.environ.get("DOCAI_AZURE__APPINSIGHTS_CONNECTION_STRING")
    if conn:  # logs, requests and dependency calls go to Application Insights; the app must still run without it
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor
            configure_azure_monitor(connection_string=conn)
        except Exception:  # noqa: BLE001
            logging.getLogger("docai.runtime.launch").warning("Application Insights is not available; logging to stdout only")


def _queue() -> str:
    q = os.environ.get("DOCAI_QUEUE") or os.environ.get("DOCAI_SUBSCRIPTION")
    if not q:
        raise SystemExit("DOCAI_QUEUE (or DOCAI_SUBSCRIPTION) is not set")
    return q


def drain_queue(ctx: Context, queue: str, handler: Handler, *, max_seconds: float = 1500) -> int:
    """Handles messages until a receive returns nothing, or the time is nearly up (the replica timeout is 30 minutes)."""
    deadline, total = time.monotonic() + max_seconds, 0
    while time.monotonic() < deadline:
        n = process_queue(ctx, queue, handler)
        total += n
        if n == 0:
            break
    return total


def queue_job(handler: Handler) -> None:
    configure_logging()
    n = drain_queue(new_context(), _queue(), handler)
    log.info("handled %d message(s); exiting", n)


def scheduled(run: Callable[[Context], object]) -> None:
    configure_logging()
    log.info("pass finished: %s", run(new_context()))


def queue_consumer(handler: Handler, *, idle_sleep: float = 2.0) -> None:
    configure_logging()
    ctx, queue = new_context(), _queue()
    while True:
        if process_queue(ctx, queue, handler) == 0:
            time.sleep(idle_sleep)


def http_app(factory: Callable[..., object], **kw) -> None:
    import uvicorn

    configure_logging()
    uvicorn.run(
        factory(new_context(), **kw), 
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", "8000")), 
        log_config=None
        )


def web_app(create_app: Callable[..., Any], msal_flow: Callable[..., Any]) -> None:
    """app-web: the sign-in secret comes from Key Vault through the app's own identity; 
    locally it is an environment variable."""
    import uvicorn

    configure_logging()
    
    ctx = new_context()
    secret = (os.environ.get("DOCAI_AUTH__WEB_CLIENT_SECRET") or 
            ctx.settings.auth.web_client_secret)
    
    if ctx.settings.azure.key_vault_uri and (
        not secret or ctx.settings.session_secret.startswith("dev-only")):
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        
        vault = SecretClient(ctx.settings.azure.key_vault_uri, DefaultAzureCredential())
        secret = secret or vault.get_secret("web-client-secret").value
        if ctx.settings.session_secret.startswith("dev-only"):  # every replica must sign with the same key
            ctx.settings.session_secret = vault.get_secret("web-session-secret").value
    uvicorn.run(
        create_app(ctx, msal_flow=msal_flow(ctx, secret or "")), 
        host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), 
        log_config=None
        )
