"""Checks the account, installs the CLI extensions, registers the resource providers and checks model quota."""
from __future__ import annotations

import json

from .lib import Ctx, DeployError

PROVIDERS = [
    "Microsoft.App", "Microsoft.ServiceBus", "Microsoft.Search", "Microsoft.DBforPostgreSQL", "Microsoft.Storage",
    "Microsoft.OperationalInsights", "Microsoft.KeyVault", "Microsoft.ManagedIdentity", "Microsoft.Insights",
    "Microsoft.ContainerRegistry", "Microsoft.CognitiveServices", "Microsoft.Authorization",
]


def run(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    if not az.signed_in():
        raise DeployError("not signed in: run 'az login'")
    ctx.log(f"subscription {ctx.sub_id}, tenant {ctx.tenant_id}, region {n.loc}, prefix {ctx.cfg.prefix}, suffix {n.suffix}")

    # containerapp is a preview extension: --scale-rule-identity (identity-based Service Bus scale rules) is only in its newer builds
    for ext, extra in (("containerapp", ["--allow-preview", "true"]), ("application-insights", [])):
        az.ensure(["extension", "show", "-n", ext], ["extension", "add", "-n", ext, "--upgrade", "-y", *extra])

    # Registration takes minutes the first time: start all of them, then wait.
    for p in PROVIDERS:
        state = az.query(["provider", "show", "-n", p], "registrationState", "Unknown")
        if state != "Registered":
            ctx.log(f"registering {p} (was {state or 'Unknown'})")
            az.run(["provider", "register", "-n", p])
    for p in PROVIDERS:
        if not az.wait(["provider", "show", "-n", p], "registrationState", "Registered", tries=60, delay=10):
            raise DeployError(f"{p} is still not registered; run this step again in a few minutes")
    ctx.log("providers registered")

    # Every model deployment needs free capacity in the chosen region.
    for model, _version, sku, cap in ctx.cfg.models:
        usage = json.loads(az.query(
            ["cognitiveservices", "usage", "list", "-l", n.loc], f"[?name.value=='OpenAI.{sku}.{model}'] | [0].{{limit:limit, used:currentValue}}",
            placeholder='{"limit": 1, "used": 0}', out="json") or "{}")
        if int(float(usage.get("limit") or 0)) <= 0:
            raise DeployError(f"no quota for {model} ({sku}) in {n.loc}. Pick another model in .env, request quota in the portal, "
                              "or set DOCAI_LOCATION to the fallback region (DOCAI_LOCATION_FALLBACK)")
        ctx.log(f"quota {model} ({sku}): limit {int(float(usage['limit']))}, used {int(float(usage.get('used') or 0))}, need {cap}")

    ctx.state.set("SUFFIX", n.suffix)
    ctx.log("preflight ok")
