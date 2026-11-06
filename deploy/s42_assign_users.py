"""Assigns app roles and group memberships to the test users. The users must already exist (docs/azure-setup.md).
Set their sign-in names in .env: DOCAI_USER_LAYLA=..., DOCAI_USER_SARA=..., DOCAI_USER_RANA=..., DOCAI_USER_YOUSEF=...
(and optionally DOCAI_USER_HUDA for the HR isolation test)."""
from __future__ import annotations

from .lib import Ctx, stable_id

GRAPH = "https://graph.microsoft.com/v1.0"
DEFAULT_ACCESS = "00000000-0000-0000-0000-000000000000"  # the sign-in app has no roles of its own
USERS = [  # env var, app role, groups
    ("DOCAI_USER_LAYLA", "DocAI.Reader", ["FIN_READERS"]),
    ("DOCAI_USER_SARA", "DocAI.Expert", ["FIN_READERS", "FIN_EXPERTS", "FIN_TREASURY"]),
    ("DOCAI_USER_RANA", "DocAI.Steward", ["FIN_READERS", "FIN_STEWARDS"]),
    ("DOCAI_USER_YOUSEF", "DocAI.Admin", []),
    ("DOCAI_USER_HUDA", "DocAI.Reader", ["HR_READERS"]),
]


def _assign(ctx: Ctx, uid: str, resource_id: str, role_id: str) -> None:
    """Idempotent: skip when the user already has an assignment on this resource (for this role, when `role_id` is a role)."""
    url = f"{GRAPH}/users/{uid}/appRoleAssignments"
    match = f"appRoleId=='{role_id}' && " if role_id != DEFAULT_ACCESS else ""
    if ctx.az.rest("get", url, query=f"value[?{match}resourceId=='{resource_id}'] | length(@)") == "1":
        return
    ctx.az.rest("post", url, {"principalId": uid, "resourceId": resource_id, "appRoleId": role_id})


def run(ctx: Ctx) -> None:
    az = ctx.az
    api_sp = ctx.need("API_SP_ID")
    web_sp = az.query(["ad", "sp", "show", "--id", ctx.need("AUTH_WEB_CLIENT_ID")], "id", "web-sp")
    for var, role, groups in USERS:
        upn = ctx.cfg.users.get(var)
        if not upn:
            ctx.warn(f"{var} is not set; skipping")
            continue
        uid = az.query(["ad", "user", "show", "--id", upn], "id", f"user-{upn}")
        _assign(ctx, uid, api_sp, stable_id(role))
        _assign(ctx, uid, web_sp, DEFAULT_ACCESS)  # the sign-in app also requires assignment
        for g in groups:
            gid = ctx.need(f"GROUP_{g}")
            if az.query(["ad", "group", "member", "check", "--group", gid, "--member-id", uid], "value") != "true":
                az.run(["ad", "group", "member", "add", "--group", gid, "--member-id", uid])
        ctx.log(f"{upn}: {role}, groups: {' '.join(groups)}")
