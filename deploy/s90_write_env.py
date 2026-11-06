"""Writes the endpoints and IDs produced by the deployment into .env (keeps a backup), so the app can run against Azure
from this machine: set DOCAI_ADAPTERS=azure. Does nothing in a dry run."""
from __future__ import annotations

import shutil

from dotenv import set_key

from .config import ROOT
from .lib import Ctx


def run(ctx: Ctx) -> None:
    if ctx.az.dry_run:
        ctx.log("[dry-run] would write the endpoints into .env")
        return
    env_file, st, n = ctx.cfg.env_file, ctx.state.get, ctx.n
    if not env_file.exists():
        shutil.copy(ROOT / ".env.example", env_file)
    shutil.copy(env_file, env_file.with_name(env_file.name + ".bak"))
    values = {
        "DOCAI_AZURE__SUBSCRIPTION_ID": ctx.sub_id, "DOCAI_AZURE__TENANT_ID": ctx.tenant_id,
        "DOCAI_AZURE__SERVICEBUS_NAMESPACE": st("SERVICEBUS_NAMESPACE"),
        "DOCAI_AZURE__STORAGE_RAW_ACCOUNT": st("STORAGE_RAW_ACCOUNT"), "DOCAI_AZURE__STORAGE_PROC_ACCOUNT": st("STORAGE_PROC_ACCOUNT"),
        "DOCAI_AZURE__STORAGE_STAGING_ACCOUNT": st("STORAGE_STAGING_ACCOUNT"),
        "DOCAI_DATABASE__HOST": st("DB_HOST"), "DOCAI_DATABASE__NAME": st("DB_NAME"),
        "DOCAI_DATABASE__USER": st("DB_ADMIN"),  # from this machine you are the administrator; the containers use their identity's name
        "DOCAI_DATABASE__ENTRA_AUTH": "true",
        "DOCAI_AZURE__SEARCH_ENDPOINT": st("SEARCH_ENDPOINT"), "DOCAI_AZURE__FOUNDRY_ENDPOINT": st("FOUNDRY_ENDPOINT"),
        "DOCAI_AZURE__FOUNDRY_PROJECT_ENDPOINT": st("FOUNDRY_PROJECT_ENDPOINT"), "DOCAI_AZURE__OCR_ENDPOINT": st("OCR_ENDPOINT"),
        "DOCAI_AZURE__CONTENT_SAFETY_ENDPOINT": st("CONTENT_SAFETY_ENDPOINT"),
        "DOCAI_AZURE__KEY_VAULT_URI": f"https://{n.kv}.vault.azure.net/",
        "DOCAI_AZURE__APPINSIGHTS_CONNECTION_STRING": st("APPINSIGHTS_CONNECTION_STRING"),
        "DOCAI_AUTH__TENANT_ID": st("AUTH_TENANT_ID"), "DOCAI_AUTH__API_CLIENT_ID": st("AUTH_API_CLIENT_ID"),
        "DOCAI_AUTH__WEB_CLIENT_ID": st("AUTH_WEB_CLIENT_ID"),
    }
    for key, value in values.items():
        if value:
            set_key(env_file, key, value, quote_mode="never")
    ctx.log(f".env updated (backup: {env_file.name}.bak). The web client secret stays in Key Vault; it is not written here.")
