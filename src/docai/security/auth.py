"""Token validation (spec, Workflow 7). Every app validates the token it receives, so no app trusts a caller because of
where the call came from. Entra tokens are checked against the tenant's signing keys; local development uses tokens
signed with a development key and carrying the same claims."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import jwt

from .access import Principal
from docai.contracts.enums import AppRole
from docai.core.settings import Settings

DOCAI_ROLES = {r.value for r in AppRole}


class AuthError(Exception):
    """The token is missing, invalid, expired or carries no DocAI role."""


def principal_from_claims(claims: dict[str, Any]) -> Principal:
    if "_claim_names" in claims and "groups" in claims["_claim_names"]:
        # Over 200 groups: Entra sends a pointer instead of the list. The fix is P1 and ApplicationGroup (spec, Open items).
        raise AuthError("the token has too many groups to carry; this tenant needs the P1 groups setup")
    roles = [r for r in claims.get("roles", []) if r in DOCAI_ROLES]
    if not roles:
        raise AuthError("the token carries no DocAI role")
    return Principal(oid=claims["oid"], name=claims.get("name", ""), roles=roles, groups=list(claims.get("groups", [])))


class DevIdentity:
    """HS256 tokens signed with a development key. Never valid in Azure: the adapter is chosen by DOCAI_ADAPTERS."""

    def __init__(self, key: str, audience: str = "api://docai-api") -> None:
        self.key, self.audience = key, audience

    def issue(self, p: Principal, ttl: int = 3600, now: float | None = None) -> str:
        t = int(now if now is not None else time.time())
        return jwt.encode({"aud": self.audience, "iss": "docai-dev", "oid": p.oid, "name": p.name, "roles": p.roles, "groups": p.groups,
                        "iat": t, "exp": t + ttl}, self.key, algorithm="HS256")

    def validate(self, token: str) -> Principal:
        try:
            return principal_from_claims(jwt.decode(token, self.key, algorithms=["HS256"], audience=self.audience, issuer="docai-dev"))
        except jwt.PyJWTError as e:
            raise AuthError(str(e)) from e


class EntraIdentity:
    """Validates Entra v2 access tokens: signature (tenant JWKS), issuer, audience, expiry."""

    def __init__(self, tenant_id: str, api_client_id: str) -> None:
        self.tenant_id, self.client_id = tenant_id, api_client_id
        self._jwks = jwt.PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys", cache_keys=True)

    def validate(self, token: str) -> Principal:
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, key, algorithms=["RS256"], audience=[f"api://{self.client_id}", self.client_id],
                                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0")
        except jwt.PyJWTError as e:
            raise AuthError(str(e)) from e
        return principal_from_claims(claims)


def build_identity(s: Settings):
    if s.adapters == "local":
        return DevIdentity(s.auth.dev_signing_key)
    return EntraIdentity(s.auth.tenant_id, s.auth.api_client_id)


@dataclass
class Session:
    """What app-web keeps for a signed-in user: the access token it forwards, and the display name."""
    token: str
    name: str
    expires_at: float
