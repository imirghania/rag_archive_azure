"""The catalogue of jobs and apps (spec, Container Apps catalog and Service identities) as data.

The deployment (`python -m deploy`) imports this module, so the queue a job consumes,
the identity it runs as and the rights it gets are written down exactly once."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from docai.contracts.messages import QUEUES, SUBSCRIPTION_NOTIFY, TOPIC

# Storage containers and the account that holds each one
CONTAINERS = {"raw": "raw", "extracted": "proc", "curated": "proc", "staging": "staging", "quarantine": "staging"}

Role = Literal["r", "rw"]


@dataclass(frozen=True)
class Component:
    name: str
    kind: Literal["job", "app"]
    module: str  # python module run by the container: python -m docai.modules.<module>
    consumes_queue: str | None = None
    consumes_subscription: str | None = None
    schedule: str | None = None  # cron, for scheduled jobs
    sends: tuple[str, ...] = ()  # queues, or the topic name
    containers: dict[str, Role] = field(default_factory=dict)
    sql_role: str | None = None  # the PostgreSQL role (r_*) the identity's database user joins; the name is kept from the Azure SQL version
    search: Literal["reader", "contributor"] | None = None
    foundry: bool = False  # Cognitive Services User on the AI Services account (models, OCR, content safety)
    keyvault: bool = False
    public: bool = False
    min_replicas: int = 0  # apps only
    max_executions: int = 5  # jobs only: also the throttle on the service quotas
    messages_per_execution: int = 10
    port: int = 8000
    cpu: float = 0.5
    memory: str = "1Gi"
    peek_all_dead_letters: bool = False

    @property
    def identity(self) -> str:
        return f"id-{self.name}"


def _j(name, module, queue, **kw):
    return Component(name, "job", module, consumes_queue=queue, **kw)


def _a(name, module, **kw):
    return Component(name, "app", module, **kw)


COMPONENTS: tuple[Component, ...] = (
    _j("job-intake", "intake", "q-intake", sends=("q-preprocess", "q-digital"),
    containers={"raw": "r", "extracted": "rw"}, sql_role="r_pipeline", max_executions=5),
    
    _j("job-upload-commit", "upload_commit", "q-upload-commit", sends=("q-upload-commit", "q-intake", TOPIC), containers={"staging": "rw", "raw": "rw", "quarantine": "rw"}, 
    sql_role="r_pipeline", max_executions=3, messages_per_execution=1),
    
    _j("job-digital", "digital", "q-digital", sends=("q-preprocess",), containers={"raw": "r", "extracted": "rw"}, sql_role="r_pipeline", max_executions=3, memory="2Gi", cpu=1.0),
    
    _j("job-preprocess", "preprocess", "q-preprocess", sends=("q-ocr-online",), containers={"raw": "r", "extracted": "rw"}, sql_role="r_pipeline", max_executions=3, messages_per_execution=1, memory="4Gi", cpu=2.0),
    
    _j("job-ocr-online", "ocr", "q-ocr-online", sends=("q-handwriting-online", "q-reconcile"),
    containers={"extracted": "rw"}, sql_role="r_pipeline", foundry=True, max_executions=10, memory="2Gi", cpu=1.0),
    
    _j("job-handwriting-online", "handwriting", "q-handwriting-online", sends=("q-reconcile",),
    containers={"extracted": "rw"}, sql_role="r_pipeline", foundry=True, max_executions=10, messages_per_execution=5),
    
    _j("job-reconcile", "reconcile", "q-reconcile", sends=("q-segment",), containers={"extracted": "rw"}, sql_role="r_pipeline", max_executions=10, messages_per_execution=20),
    
    _j("job-segment", "segment", "q-segment", sends=("q-metadata", TOPIC), 
    containers={"extracted": "rw"}, sql_role="r_pipeline", foundry=True, max_executions=3, messages_per_execution=1),
    
    _j("job-metadata", "metadata", "q-metadata", sends=("q-chunk",), 
    containers={"extracted": "rw"}, sql_role="r_pipeline", foundry=True, max_executions=5, messages_per_execution=5),
    
    _j("job-chunk-embed", "chunk_embed", "q-chunk", sends=("q-index",), 
    containers={"extracted": "r", "curated": "rw"}, sql_role="r_pipeline", foundry=True, max_executions=5, messages_per_execution=2),
    
    _j("job-index", "index", "q-index", sends=(TOPIC,), containers={"curated": "r"}, sql_role="r_pipeline", search="contributor", max_executions=5, messages_per_execution=5),
    
    _j("job-post-review", "post_review", "q-post-review", sends=("q-chunk",), 
    containers={"extracted": "rw"}, sql_role="r_pipeline", max_executions=3, messages_per_execution=5),
    
    Component("job-watchdog", "job", "watchdog", schedule="*/10 * * * *", peek_all_dead_letters=True,
    sends=("q-ocr-online", "q-handwriting-online", "q-reconcile", "q-segment", TOPIC), containers={"extracted": "rw"}, sql_role="r_pipeline"),
    
    # apps
    _a("app-web", "web", public=True, keyvault=True, port=8000, min_replicas=1),
    
    _a("app-upload-api", "upload_api", sends=("q-upload-commit",), containers={"staging": "rw"}, sql_role="r_upload"),
    
    _a("app-chat-api", "chat_api", sends=("q-index",), containers={"extracted": "r"}, sql_role="r_chat", search="reader", foundry=True),
    
    _a("app-retrieval", "retrieval", sql_role="r_lookup", search="reader", foundry=True),  # foundry: it embeds the query
    
    _a("app-verifier", "verifier", sql_role="r_lookup", foundry=True),
    # the outbox relay loop lives in app-review, so it never scales to zero (spec, Mechanics)
    
    _a("app-review", "review", sends=("q-post-review", "q-index", "q-hint-events", "q-intake", TOPIC), containers={"extracted": "rw"}, sql_role="r_review", min_replicas=1),
    
    _a("app-hint-worker", "hint_worker", consumes_queue="q-hint-events", sends=(TOPIC,), sql_role="r_hint", search="contributor", foundry=True),
    
    _a("app-notifier", "notifier", consumes_subscription=SUBSCRIPTION_NOTIFY, sql_role="r_notifier"),
)

BY_NAME = {c.name: c for c in COMPONENTS}


def jobs() -> list[Component]:
    return [c for c in COMPONENTS if c.kind == "job"]


def apps() -> list[Component]:
    return [c for c in COMPONENTS if c.kind == "app"]


def role_assignments(c: Component) -> list[tuple[str, str, str]]:
    """(role, scope kind, scope name) rows for one component. Scope kinds: queue, topic, subscription,
    container, search, foundry, keyvault. Roles are the built-in Azure role names."""
    rows: list[tuple[str, str, str]] = []
    if c.consumes_queue:
        rows.append(("Azure Service Bus Data Receiver", "queue", c.consumes_queue))
    if c.consumes_subscription:
        rows.append(("Azure Service Bus Data Receiver", "subscription", c.consumes_subscription))
    if c.peek_all_dead_letters:
        rows += [("Azure Service Bus Data Receiver", "queue", q) for q in QUEUES if q != c.consumes_queue]
    for dest in c.sends:
        sender = ("Azure Service Bus Data Sender", "topic" if dest == TOPIC else "queue", dest)
        if sender not in rows:
            rows.append(sender)
    for container, mode in c.containers.items():
        role = "Storage Blob Data Contributor" if mode == "rw" else "Storage Blob Data Reader"
        rows.append((role, "container", container))
    if c.search:
        rows.append(("Search Index Data Contributor" if c.search == "contributor" else "Search Index Data Reader", "search", "service"))
        if c.search == "contributor" and c.name == "app-hint-worker":
            rows.append(("Search Service Contributor", "search", "service"))  # replaces the synonym maps
    if c.foundry:
        rows.append(("Cognitive Services User", "foundry", "account"))
        if c.name == "app-chat-api":
            rows.append(("Foundry User", "foundry", "account"))  # runs the Foundry agent
    if c.keyvault:
        rows.append(("Key Vault Secrets User", "keyvault", "vault"))
    return rows
