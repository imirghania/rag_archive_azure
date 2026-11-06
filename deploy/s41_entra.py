"""Entra ID (Free tier): two app registrations, app roles, the API scope, security groups, and the web client secret in Key Vault.
Needs a signed-in user who may register applications and create groups. If this fails with "Insufficient privileges",
follow docs/azure-setup.md (portal steps) instead."""
from __future__ import annotations

import secrets

from .lib import Ctx, stable_id
from .s42_assign_users import GRAPH

API_NAME, WEB_NAME = "docai-api", "docai-web"
LOCAL_REDIRECT = "http://localhost:8000/auth/callback"
ROLES = [
    ("DocAI.Reader", "Reader", "Ask questions, open citations, give feedback"),
    ("DocAI.Expert", "Expert", "Settle review tasks, submit hints, upload files"),
    ("DocAI.Steward", "Steward", "Approve and revoke hints, restrict dossiers, settle escalated tasks"),
    ("DocAI.Admin", "Admin", "Department registry, status and reprocess; no content access"),
    ("DocAI.Uploader", "Uploader", "Reserved: upload only"),
    ("DocAI.Auditor", "Auditor", "Reserved: read audit records"),
]
GROUPS = {  # state key -> group name; the registry rows are seeded from these IDs by the bootstrap
    "FIN_READERS": "grp-docai-fin-readers", "FIN_EXPERTS": "grp-docai-fin-experts", "FIN_STEWARDS": "grp-docai-fin-stewards",
    "FIN_TREASURY": "grp-docai-fin-treasury", "HR_READERS": "grp-docai-hr-readers",
}


def _app(ctx: Ctx, name: str, placeholder: str, extra: list[str]) -> str:
    """The client ID of the app registration `name`: found by display name, or created."""
    return ctx.az.query(["ad", "app", "list", "--display-name", name], "[0].appId") or ctx.az.run(
        ["ad", "app", "create", "--display-name", name, "--sign-in-audience", "AzureADMyOrg", *extra], query="appId", placeholder=placeholder)


def _service_principal(ctx: Ctx, client_id: str, placeholder: str) -> str:
    """Its service principal (created if missing), set so that only assigned users get a token (AADSTS50105 for the others)."""
    az = ctx.az
    az.ensure(["ad", "sp", "show", "--id", client_id], ["ad", "sp", "create", "--id", client_id])
    sp_id = az.query(["ad", "sp", "show", "--id", client_id], "id", placeholder)
    az.rest("patch", f"{GRAPH}/servicePrincipals/{sp_id}", {"appRoleAssignmentRequired": True})
    return sp_id


def run(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    scope_id = stable_id("access_as_user")  # fixed IDs: a rerun never creates a second role or scope with a new ID
    app_roles = [{"id": stable_id(v), "value": v, "displayName": d, "description": desc, "allowedMemberTypes": ["User"], "isEnabled": True}
                 for v, d, desc in ROLES]
    scope = [{"id": scope_id, "value": "access_as_user", "type": "User", "isEnabled": True, "adminConsentDisplayName": "Use DocAI",
              "adminConsentDescription": "Access DocAI on behalf of the signed-in user", "userConsentDisplayName": "Use DocAI",
              "userConsentDescription": "Access DocAI on your behalf"}]

    api_id = _app(ctx, API_NAME, "api-app-id", [])
    api_obj = az.query(["ad", "app", "show", "--id", api_id], "id", "api-object-id")  # Graph URLs take the object ID, not the client ID
    api_patch = {"requestedAccessTokenVersion": 2, "oauth2PermissionScopes": scope}
    az.rest("patch", f"{GRAPH}/applications/{api_obj}", {
        "identifierUris": [f"api://{api_id}"], "appRoles": app_roles, "groupMembershipClaims": "SecurityGroup", "api": api_patch})
    api_sp = _service_principal(ctx, api_id, "api-sp")

    web_id = _app(ctx, WEB_NAME, "web-app-id", ["--web-redirect-uris", LOCAL_REDIRECT])
    _service_principal(ctx, web_id, "web-sp")
    # Pre-authorize the web app for the API scope, so users are not asked for consent.
    az.rest("patch", f"{GRAPH}/applications/{api_obj}", {
        "api": {**api_patch, "preAuthorizedApplications": [{"appId": web_id, "delegatedPermissionIds": [scope_id]}]}})
    az.run(["ad", "app", "permission", "add", "--id", web_id, "--api", api_id, "--api-permissions", f"{scope_id}=Scope"])

    # Web client secret: created once, stored in Key Vault, never printed. A rerun keeps the existing secret.
    # Cookie signing key of app-web, shared by all its replicas: also created once. `--value=` because a value may start with '-'.
    if not az.exists(["keyvault", "secret", "show", "--vault-name", n.kv, "-n", "web-client-secret"]):
        secret = az.run(["ad", "app", "credential", "reset", "--id", web_id, "--display-name", "docai-web-secret", "--years", "1"],
                        query="password", placeholder="secret")
        az.run(["keyvault", "secret", "set", "--vault-name", n.kv, "-n", "web-client-secret", f"--value={secret}"])
    if not az.exists(["keyvault", "secret", "show", "--vault-name", n.kv, "-n", "web-session-secret"]):
        session = "session-secret" if az.dry_run else secrets.token_urlsafe(48)
        az.run(["keyvault", "secret", "set", "--vault-name", n.kv, "-n", "web-session-secret", f"--value={session}"])

    # Security groups (static: dynamic groups need Entra P1).
    for key, name in GROUPS.items():
        gid = az.query(["ad", "group", "list", "--display-name", name], "[0].id") or az.run(
            ["ad", "group", "create", "--display-name", name, "--mail-nickname", name], query="id", placeholder=f"group-id-{name}")
        ctx.state.set(f"GROUP_{key}", gid)

    ctx.state.set("AUTH_TENANT_ID", ctx.tenant_id)
    ctx.state.set("AUTH_API_CLIENT_ID", api_id)
    ctx.state.set("AUTH_WEB_CLIENT_ID", web_id)
    ctx.state.set("API_SP_ID", api_sp)
    ctx.log("entra ok. Next: create the four users (docs/azure-setup.md, step 3), then run step 42")
