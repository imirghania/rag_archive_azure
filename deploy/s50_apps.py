"""Builds the image in ACR (no local Docker needed) and creates every job and app of the catalogue.
Components whose module does not exist yet in src/docai/modules are skipped, so this can run before the code is finished."""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from functools import partial

from docai.core import catalog

from .config import ROOT
from .lib import Ctx, DeployError, git_short_sha, key_of

REPLICA_TIMEOUT = "1800"
# The containerapp extension now and then crashes inside its own error handler (it parses a non-JSON error of a read call) and prints
# "The command failed with an unexpected error". The same create works a moment later (found on the first real run, D49).
TRANSIENT = "unexpected error"


def _module_exists(module: str) -> bool:
    base = ROOT / "src" / "docai" / "modules"
    return (base / f"{module}.py").is_file() or (base / module / "__main__.py").is_file()


def _common_env(ctx: Ctx) -> list[str]:
    n, cfg, st = ctx.n, ctx.cfg, ctx.need
    ais = f"https://{n.ais}.cognitiveservices.azure.com/"
    env = {
        "DOCAI_ADAPTERS": "azure", "DOCAI_ENV": cfg.env,
        "DOCAI_AZURE__SERVICEBUS_NAMESPACE": n.sb_fqdn,
        "DOCAI_AZURE__STORAGE_RAW_ACCOUNT": n.st_raw, "DOCAI_AZURE__STORAGE_PROC_ACCOUNT": n.st_proc,
        "DOCAI_AZURE__STORAGE_STAGING_ACCOUNT": n.st_stg,
        "DOCAI_DATABASE__HOST": n.pg_host, "DOCAI_DATABASE__NAME": cfg.db_name, "DOCAI_DATABASE__ENTRA_AUTH": "true",
        "DOCAI_AZURE__SEARCH_ENDPOINT": f"https://{n.search}.search.windows.net",
        "DOCAI_AZURE__FOUNDRY_ENDPOINT": ais,
        "DOCAI_AZURE__FOUNDRY_PROJECT_ENDPOINT": st("FOUNDRY_PROJECT_ENDPOINT"),
        "DOCAI_AZURE__OCR_ENDPOINT": ais, "DOCAI_AZURE__CONTENT_SAFETY_ENDPOINT": ais,
        "DOCAI_AZURE__KEY_VAULT_URI": f"https://{n.kv}.vault.azure.net/",
        "DOCAI_AZURE__APPINSIGHTS_CONNECTION_STRING": st("APPINSIGHTS_CONNECTION_STRING"),
        "DOCAI_AUTH__TENANT_ID": ctx.tenant_id, "DOCAI_AUTH__API_CLIENT_ID": st("AUTH_API_CLIENT_ID"),
        "DOCAI_AUTH__WEB_CLIENT_ID": st("AUTH_WEB_CLIENT_ID"),
        **cfg.model_env,
    }
    return [f"{k}={v}" for k, v in env.items()]


def _component_env(ctx: Ctx, c: catalog.Component, common: list[str]) -> list[str]:
    env = [*common, f"AZURE_CLIENT_ID={ctx.need('CID_' + key_of(c.name))}", f"DOCAI_COMPONENT={c.name}"]
    if c.consumes_queue:
        env.append(f"DOCAI_QUEUE={c.consumes_queue}")
    if c.consumes_subscription:
        env.append(f"DOCAI_SUBSCRIPTION={c.consumes_subscription}")
    if c.sql_role:  # the database role has the name of the identity (bootstrap `users`)
        env.append(f"DOCAI_DATABASE__USER={c.identity}")
    return env


def _scale_rule(ctx: Ctx, c: catalog.Component, idr: str, messages: int) -> list[str]:
    n = ctx.n
    if c.consumes_queue:
        name, meta = f"sb-{c.consumes_queue}", [f"queueName={c.consumes_queue}"]
    elif c.consumes_subscription:
        name, meta = f"sb-{c.consumes_subscription}", [f"topicName={n.topic}", f"subscriptionName={c.consumes_subscription}"]
    else:
        return []
    return ["--scale-rule-name", name, "--scale-rule-type", "azure-servicebus", "--scale-rule-metadata",
            f"namespace={n.sbns}", *meta, f"messageCount={messages}", "--scale-rule-identity", idr]


def _retrying(ctx: Ctx, name: str, deploy: Callable[[], None], tries: int = 3, wait: int = 30) -> None:
    """Run one component's deployment again after that transient crash. Safe: each deployment probes first, then creates or updates."""
    for attempt in range(1, tries + 1):
        try:
            return deploy()
        except DeployError as e:
            if attempt == tries or TRANSIENT not in str(e):
                raise
            ctx.warn(f"{name}: the Azure CLI extension failed on a transient error, retrying in {wait}s ({attempt}/{tries})")
            time.sleep(wait)


def _deploy_job(ctx: Ctx, c: catalog.Component, image: str, env: list[str], idr: str) -> None:
    az, n = ctx.az, ctx.n
    if az.exists(["containerapp", "job", "show", "-g", n.rg, "-n", c.name]):
        az.run(["containerapp", "job", "update", "-g", n.rg, "-n", c.name, "--image", image, "--set-env-vars", *env])
        return
    if c.schedule:
        trigger = ["--trigger-type", "Schedule", "--cron-expression", c.schedule]
    else:
        trigger = ["--trigger-type", "Event", "--min-executions", "0", "--max-executions", str(c.max_executions), "--polling-interval", "30",
                   *_scale_rule(ctx, c, idr, c.messages_per_execution)]
    az.run(["containerapp", "job", "create", "-g", n.rg, "-n", c.name, "--environment", n.cae, *trigger, "--image", image,
            "--cpu", str(c.cpu), "--memory", c.memory, "--mi-user-assigned", idr, "--registry-server", f"{n.acr}.azurecr.io",
            "--registry-identity", idr, "--replica-timeout", REPLICA_TIMEOUT, "--replica-retry-limit", "1",
            "--env-vars", *env, "--command", "docai-run", c.module])


def _deploy_app(ctx: Ctx, c: catalog.Component, image: str, env: list[str], idr: str) -> None:
    az, n = ctx.az, ctx.n
    consumer = bool(c.consumes_queue or c.consumes_subscription)
    if az.exists(["containerapp", "show", "-g", n.rg, "-n", c.name]):
        az.run(["containerapp", "update", "-g", n.rg, "-n", c.name, "--image", image, "--set-env-vars", *env])
    else:
        ingress = [] if consumer else ["--ingress", "external" if c.public else "internal", "--target-port", str(c.port)]
        az.run(["containerapp", "create", "-g", n.rg, "-n", c.name, "--environment", n.cae, "--image", image,
                "--cpu", str(c.cpu), "--memory", c.memory, "--user-assigned", idr, "--registry-server", f"{n.acr}.azurecr.io",
                "--registry-identity", idr, *ingress, "--min-replicas", str(c.min_replicas), "--max-replicas", "3",
                *_scale_rule(ctx, c, idr, 5), "--env-vars", *env, "--command", "docai-run", c.module])
    if not consumer and not c.public:  # internal calls between apps use http://<app name>
        az.run(["containerapp", "ingress", "update", "-g", n.rg, "-n", c.name, "--allow-insecure", "true"])


def run(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    # A new tag on every build: a rebuild under the same tag would not be rolled out to running apps.
    tag = os.environ.get("IMAGE_TAG") or f"{git_short_sha()}-{time.strftime('%Y%m%d%H%M%S')}"
    image = f"{n.acr}.azurecr.io/docai:{tag}"
    ctx.log(f"building {image}")
    az.run(["acr", "build", "-r", n.acr, "-t", f"docai:{tag}", "-f", str(ROOT / "deploy" / "Dockerfile"), str(ROOT)])

    common = _common_env(ctx)
    for c in catalog.COMPONENTS:
        if not _module_exists(c.module):
            ctx.warn(f"skip {c.name}: src/docai/modules/{c.module} is not written yet")
            continue
        idr = ctx.scope(f"Microsoft.ManagedIdentity/userAssignedIdentities/{c.identity}")
        deploy = _deploy_job if c.kind == "job" else _deploy_app
        _retrying(ctx, c.name, partial(deploy, ctx, c, image, _component_env(ctx, c, common), idr))
        ctx.log(f"{c.name} deployed")

    # app-web is public: print its address and add it as a redirect URI of the sign-in app.
    if az.exists(["containerapp", "show", "-g", n.rg, "-n", "app-web"]):
        fqdn = az.query(["containerapp", "show", "-g", n.rg, "-n", "app-web"], "properties.configuration.ingress.fqdn")
        callback = f"https://{fqdn}/auth/callback"
        az.run(["containerapp", "update", "-g", n.rg, "-n", "app-web", "--set-env-vars", f"DOCAI_WEB_REDIRECT_URL={callback}"])
        az.run(["ad", "app", "update", "--id", ctx.need("AUTH_WEB_CLIENT_ID"), "--web-redirect-uris", callback, "http://localhost:8000/auth/callback"])
        ctx.log(f"app-web: https://{fqdn}")
    ctx.log("apps ok")
