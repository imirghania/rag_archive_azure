"""Storage (3 accounts), Service Bus (queues, topic, subscription), PostgreSQL, AI Search."""
from __future__ import annotations

import json

from docai.contracts.messages import NOTIFY_TYPES, QUEUES, SUBSCRIPTION_NOTIFY

from . import config
from .lib import Ctx, DeployError


def _lifecycle(name: str, prefix: str, action: dict) -> str:
    rule = {"name": name, "enabled": True, "type": "Lifecycle", "definition": {
        "filters": {"blobTypes": ["blockBlob"], "prefixMatch": [prefix]}, "actions": {"baseBlob": action}}}
    return json.dumps({"rules": [rule]})


def _storage(ctx: Ctx, account: str, sku: str, containers: list[str]) -> None:
    az, n = ctx.az, ctx.n
    az.ensure(["storage", "account", "show", "-g", n.rg, "-n", account],
              ["storage", "account", "create", "-g", n.rg, "-n", account, "-l", n.loc, "--sku", sku, "--kind", "StorageV2", "--hns", "true",
               "--allow-blob-public-access", "false", "--allow-shared-key-access", "false", "--min-tls-version", "TLS1_2"])
    # Shared keys are off, so creating a container needs a data role; a new assignment can take minutes to apply.
    ctx.role(ctx.need("DEPLOYER_OID"), "Storage Blob Data Contributor", ctx.scope(f"Microsoft.Storage/storageAccounts/{account}"), "User")
    for c in containers:
        try:
            az.run(["storage", "container", "create", "--account-name", account, "-n", c, "--auth-mode", "login"], retries=10, wait=20)
        except DeployError as e:
            raise DeployError(f"cannot create container {c}: the role assignment has not applied yet; run this step again in a few minutes") from e


def _service_bus(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    sb = ["-g", n.rg, "--namespace-name", n.sbns]
    az.ensure(["servicebus", "namespace", "show", "-g", n.rg, "-n", n.sbns],
              ["servicebus", "namespace", "create", "-g", n.rg, "-n", n.sbns, "-l", n.loc, "--sku", "Standard", "--disable-local-auth", "true"])
    for q in QUEUES.values():
        az.run(["servicebus", "queue", "create", *sb, "-n", q.name, "--lock-duration", "PT5M", "--max-delivery-count", str(q.max_delivery),
                "--default-message-time-to-live", "P14D", "--enable-dead-lettering-on-message-expiration", "true",
                "--enable-duplicate-detection", "true", "--duplicate-detection-history-time-window", q.dup_window,
                "--enable-session", str(q.sessions).lower()])
    az.run(["servicebus", "topic", "create", *sb, "-n", n.topic, "--default-message-time-to-live", "P14D",
            "--enable-duplicate-detection", "true", "--duplicate-detection-history-time-window", "PT1H"])
    sub = ["--topic-name", n.topic]
    az.run(["servicebus", "topic", "subscription", "create", *sb, *sub, "-n", SUBSCRIPTION_NOTIFY, "--lock-duration", "PT5M",
            "--max-delivery-count", "5", "--default-message-time-to-live", "P14D", "--enable-dead-lettering-on-message-expiration", "true"])
    # A subscription starts with a rule that matches everything; replace it with the filter of the spec.
    az.run(["servicebus", "topic", "subscription", "rule", "delete", *sb, *sub, "--subscription-name", SUBSCRIPTION_NOTIFY, "-n", "$Default"], check=False)
    az.run(["servicebus", "topic", "subscription", "rule", "create", *sb, *sub, "--subscription-name", SUBSCRIPTION_NOTIFY, "-n", "notify-types",
            "--filter-sql-expression", "type IN (" + ", ".join(f"'{t}'" for t in NOTIFY_TYPES) + ")"])
    # The deployer may peek and send for tests.
    ctx.role(ctx.need("DEPLOYER_OID"), "Azure Service Bus Data Owner", ctx.scope(f"Microsoft.ServiceBus/namespaces/{n.sbns}"), "User")


def _postgres(ctx: Ctx) -> None:
    """Entra-only authentication: the signed-in user is the server's administrator; there is no database password.
    Public access is limited to Azure services (0.0.0.0 rule) plus this machine, so the bootstrap can connect."""
    az, n = ctx.az, ctx.n
    srv = ["-g", n.rg, "-s", n.pg]
    az.ensure(["postgres", "flexible-server", "show", "-g", n.rg, "-n", n.pg],
              ["postgres", "flexible-server", "create", "-g", n.rg, "-n", n.pg, "-l", n.loc, "--tier", config.POSTGRES_TIER,
               "--sku-name", config.POSTGRES_SKU, "--storage-size", str(config.POSTGRES_STORAGE_GB), "--version", config.POSTGRES_VERSION,
               "--microsoft-entra-auth", "Enabled", "--password-auth", "Disabled", "--public-access", "0.0.0.0",
               "--create-default-database", "Disabled", "--tags", "app=docai", f"env={ctx.cfg.env}", "--yes"])
    oid = ctx.need("DEPLOYER_OID")
    upn = az.query(["ad", "signed-in-user", "show"], "userPrincipalName", "deployer@example.com")
    if not az.query(["postgres", "flexible-server", "microsoft-entra-admin", "list", *srv], f"[?objectId=='{oid}'] | [0].objectId"):
        az.run(["postgres", "flexible-server", "microsoft-entra-admin", "create", *srv, "-u", upn, "-i", oid, "-t", "User"])
    if ip := ctx.public_ip():
        az.run(["postgres", "flexible-server", "firewall-rule", "create", "-g", n.rg, "-n", n.pg, "--rule-name", "deployer",
                "--start-ip-address", ip, "--end-ip-address", ip])
    az.ensure(["postgres", "flexible-server", "db", "show", *srv, "-d", ctx.cfg.db_name],
              ["postgres", "flexible-server", "db", "create", *srv, "-d", ctx.cfg.db_name])
    ctx.state.set("DB_HOST", n.pg_host)
    ctx.state.set("DB_NAME", ctx.cfg.db_name)
    ctx.state.set("DB_ADMIN", upn)  # the database role of the administrator: bootstrap --user


def _search(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    az.ensure(["search", "service", "show", "-g", n.rg, "-n", n.search],
              ["search", "service", "create", "-g", n.rg, "-n", n.search, "-l", n.loc, "--sku", "basic", "--partition-count", "1",
               "--replica-count", "1", "--auth-options", "aadOrApiKey", "--aad-auth-failure-mode", "http401WithBearerChallenge"])
    scope = ctx.scope(f"Microsoft.Search/searchServices/{n.search}")
    for role in ("Search Service Contributor", "Search Index Data Contributor"):
        ctx.role(ctx.need("DEPLOYER_OID"), role, scope, "User")


def run(ctx: Ctx) -> None:
    n = ctx.n
    _storage(ctx, n.st_raw, "Standard_LRS", ["raw"])  # production: Standard_GRS
    _storage(ctx, n.st_proc, "Standard_LRS", ["extracted", "curated"])
    _storage(ctx, n.st_stg, "Standard_LRS", ["staging", "quarantine"])

    # Staging is emptied by a lifecycle rule (7 days; the 3-day rule for abandoned uploads is applied by the upload job).
    ctx.az.run(["storage", "account", "management-policy", "create", "-g", n.rg, "--account-name", n.st_stg,
                "--policy", _lifecycle("staging-expiry", "staging/", {"delete": {"daysAfterModificationGreaterThan": 7}})])
    # crops move to the cool tier after 180 days (spec, Step 4)
    ctx.az.run(["storage", "account", "management-policy", "create", "-g", n.rg, "--account-name", n.st_proc,
                "--policy", _lifecycle("crops-cool", "extracted/", {"tierToCool": {"daysAfterModificationGreaterThan": 180}})])

    # raw is write-once: a time-based retention policy. Off by default in dev because a resource group with immutable
    # blobs cannot be deleted until the period ends. Set DOCAI_RAW_RETENTION_DAYS=2190 for production.
    if ctx.cfg.raw_retention_days > 0:
        ctx.az.run(["storage", "container", "immutability-policy", "create", "--account-name", n.st_raw, "--container-name", "raw",
                    "--period", str(ctx.cfg.raw_retention_days), "--allow-protected-append-writes", "false"])
        ctx.warn(f"raw has a {ctx.cfg.raw_retention_days}-day retention policy (unlocked). Lock it only when you are sure.")

    _service_bus(ctx)
    _postgres(ctx)
    _search(ctx)

    for key, value in {
        "SERVICEBUS_NAMESPACE": n.sb_fqdn, "STORAGE_RAW_ACCOUNT": n.st_raw, "STORAGE_PROC_ACCOUNT": n.st_proc,
        "STORAGE_STAGING_ACCOUNT": n.st_stg, "SEARCH_ENDPOINT": f"https://{n.search}.search.windows.net",
    }.items():
        ctx.state.set(key, value)
    ctx.log("data ok")
