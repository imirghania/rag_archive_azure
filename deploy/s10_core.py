"""Resource group, monitoring, container registry, Key Vault, Container Apps environment, managed identities."""
from __future__ import annotations

from docai.core import catalog

from .lib import Ctx, key_of


def run(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    az.run(["group", "create", "-n", n.rg, "-l", n.loc, "--tags", "app=docai", f"env={ctx.cfg.env}"])

    az.ensure(["monitor", "log-analytics", "workspace", "show", "-g", n.rg, "-n", n.law],
              ["monitor", "log-analytics", "workspace", "create", "-g", n.rg, "-n", n.law, "-l", n.loc, "--retention-time", "30"])
    law_id = az.query(["monitor", "log-analytics", "workspace", "show", "-g", n.rg, "-n", n.law], "customerId", "law-id")
    law_key = az.query(["monitor", "log-analytics", "workspace", "get-shared-keys", "-g", n.rg, "-n", n.law], "primarySharedKey", "law-key")

    az.ensure(["monitor", "app-insights", "component", "show", "-g", n.rg, "-a", n.appi],
              ["monitor", "app-insights", "component", "create", "-g", n.rg, "-a", n.appi, "-l", n.loc, "--workspace", n.law, "--kind", "web"])
    ctx.state.set("APPINSIGHTS_CONNECTION_STRING", az.query(
        ["monitor", "app-insights", "component", "show", "-g", n.rg, "-a", n.appi], "connectionString", "conn"))

    az.ensure(["acr", "show", "-g", n.rg, "-n", n.acr],
              ["acr", "create", "-g", n.rg, "-n", n.acr, "-l", n.loc, "--sku", "Basic", "--admin-enabled", "false"])

    # Key Vault holds the web sign-in client secret and the cookie signing key. RBAC authorization, no access policies.
    az.ensure(["keyvault", "show", "-g", n.rg, "-n", n.kv],
              ["keyvault", "create", "-g", n.rg, "-n", n.kv, "-l", n.loc, "--enable-rbac-authorization", "true", "--retention-days", "7"])
    deployer = az.query(["ad", "signed-in-user", "show"], "id", "deployer-oid")
    ctx.state.set("DEPLOYER_OID", deployer)
    ctx.role(deployer, "Key Vault Secrets Officer", ctx.scope(f"Microsoft.KeyVault/vaults/{n.kv}"), "User")

    # Container Apps environment (consumption only: no cost while nothing runs).
    az.ensure(["containerapp", "env", "show", "-g", n.rg, "-n", n.cae],
              ["containerapp", "env", "create", "-g", n.rg, "-n", n.cae, "-l", n.loc,
               "--logs-workspace-id", law_id, "--logs-workspace-key", law_key])

    # One user-assigned managed identity per job and app; each also gets AcrPull so it can start its image.
    acr_id = az.query(["acr", "show", "-g", n.rg, "-n", n.acr], "id", "acr-id")
    for c in catalog.COMPONENTS:
        az.ensure(["identity", "show", "-g", n.rg, "-n", c.identity], ["identity", "create", "-g", n.rg, "-n", c.identity, "-l", n.loc])
        oid = az.query(["identity", "show", "-g", n.rg, "-n", c.identity], "principalId", f"oid-{c.name}")
        ctx.state.set(f"OID_{key_of(c.name)}", oid)  # bootstrap `users` creates the database role from this object ID
        ctx.state.set(f"CID_{key_of(c.name)}", az.query(["identity", "show", "-g", n.rg, "-n", c.identity], "clientId", f"cid-{c.name}"))
        ctx.role(oid, "AcrPull", acr_id)
    ctx.log("core ok")
