"""Gives each managed identity exactly the rights of the catalogue (docai.core.catalog): queue send/receive, container
read/write, Search, AI Services, Key Vault. Database rights are granted by the bootstrap (`users`)."""
from __future__ import annotations

from docai.core import catalog

from .lib import Ctx, DeployError, key_of


def _scope_of(ctx: Ctx, kind: str, name: str) -> str:
    n = ctx.n
    sb = f"Microsoft.ServiceBus/namespaces/{n.sbns}"
    if kind == "queue":
        return ctx.scope(f"{sb}/queues/{name}")
    if kind == "topic":
        return ctx.scope(f"{sb}/topics/{name}")
    if kind == "subscription":
        return ctx.scope(f"{sb}/topics/{n.topic}/subscriptions/{name}")
    if kind == "container":
        return ctx.scope(f"Microsoft.Storage/storageAccounts/{n.account_of(name)}/blobServices/default/containers/{name}")
    if kind == "search":
        return ctx.scope(f"Microsoft.Search/searchServices/{n.search}")
    if kind == "foundry":
        return ctx.scope(f"Microsoft.CognitiveServices/accounts/{n.ais}")
    if kind == "keyvault":
        return ctx.scope(f"Microsoft.KeyVault/vaults/{n.kv}")
    raise DeployError(f"unknown scope kind {kind}")


def run(ctx: Ctx) -> None:
    for c in catalog.COMPONENTS:
        oid = ctx.need(f"OID_{key_of(c.name)}")
        for role, kind, target in catalog.role_assignments(c):
            ctx.role(oid, role, _scope_of(ctx, kind, target))
        ctx.log(f"rbac {c.name} done")
    ctx.log("rbac ok (role assignments can take a few minutes to take effect)")
