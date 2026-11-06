"""Deletes everything this deployment created: the resource group, the soft-deleted vault and AI account, and the
Entra apps and groups. Asks for the resource group name first (unless --yes). Never part of the default run."""
from __future__ import annotations

from .lib import Ctx, DeployError
from .s41_entra import API_NAME, GROUPS, WEB_NAME


def run(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    if not (ctx.yes or az.dry_run) and input(f"Type the resource group name ({n.rg}) to delete everything: ").strip() != n.rg:
        raise DeployError("not confirmed")
    if az.exists(["group", "show", "-n", n.rg]):
        az.run(["group", "delete", "-n", n.rg, "--yes"])
    # Soft-deleted vaults and AI accounts keep their names reserved; purge them so the next deployment can reuse the name.
    az.run(["keyvault", "purge", "--name", n.kv, "--location", n.loc], check=False)
    az.run(["cognitiveservices", "account", "purge", "-g", n.rg, "-n", n.ais, "-l", n.loc], check=False)
    for name in (API_NAME, WEB_NAME):
        if app_id := az.query(["ad", "app", "list", "--display-name", name], "[0].id"):
            az.run(["ad", "app", "delete", "--id", app_id])
    for name in GROUPS.values():
        if group_id := az.query(["ad", "group", "list", "--display-name", name], "[0].id"):
            az.run(["ad", "group", "delete", "--group", group_id])
    ctx.state.delete()
    ctx.log("teardown ok (the users you created in Entra are left alone)")
