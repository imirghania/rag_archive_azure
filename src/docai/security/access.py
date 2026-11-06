"""Access rules shared by every app (spec, Workflow 7: roles are global, capabilities are per department).

A role travels in the token as a flat list: it says the user holds DocAI.Expert somewhere, not where. So a capability is
always the role AND the department's own group of that kind. Nothing here trusts the role alone."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from docai.contracts.enums import AppRole, Capability, GroupKind

Registry = dict[str, tuple[str, str]]  # group_id -> (department, kind), from ops.access_groups


def access_scope(registry: Registry, token_groups: list[str]) -> list[str]:
    """The group IDs of the token that are registered. Unregistered groups are ignored: they can never grant access."""
    return sorted(g for g in set(token_groups) if g in registry)


def scope_hash(scope: list[str]) -> str:
    return hashlib.sha256(",".join(sorted(scope)).encode()).hexdigest()


@dataclass
class Principal:
    oid: str
    name: str
    roles: list[str]
    groups: list[str] = field(default_factory=list)


def _has(registry: Registry, groups: list[str], department: str, kind: GroupKind) -> bool:
    return any(registry.get(g) == (department, kind.value) for g in groups)


def departments_with(registry: Registry, p: Principal, cap: Capability) -> list[str]:
    """Departments where the person holds the capability: the role together with that department's own group."""
    depts = {d for d, _ in registry.values()}
    has_role = lambda r: r.value in p.roles  # noqa: E731
    out = []
    for d in sorted(depts):
        if cap is Capability.ask:
            ok = _has(registry, p.groups, d, GroupKind.reader) and any(has_role(r) for r in (AppRole.reader, AppRole.expert, AppRole.steward))
        elif cap is Capability.review:
            ok = has_role(AppRole.expert) and _has(registry, p.groups, d, GroupKind.expert) or \
                has_role(AppRole.steward) and _has(registry, p.groups, d, GroupKind.steward)
        elif cap is Capability.approve:
            ok = has_role(AppRole.steward) and _has(registry, p.groups, d, GroupKind.steward)
        elif cap is Capability.upload:
            has_uploader_group = any(v == (d, GroupKind.uploader.value) for v in registry.values())
            ok = (has_role(AppRole.uploader) and _has(registry, p.groups, d, GroupKind.uploader)) if has_uploader_group else \
                (has_role(AppRole.expert) and _has(registry, p.groups, d, GroupKind.expert))
        else:
            ok = False
        if ok:
            out.append(d)
    return out


def require(registry: Registry, p: Principal, cap: Capability, department: str) -> None:
    """Compares the department of the object being touched with the caller's departments, never 'has the role anywhere'."""
    if department not in departments_with(registry, p, cap):
        raise PermissionError(f"{cap.value} is not allowed in {department}")


def is_admin(p: Principal) -> bool:
    return AppRole.admin.value in p.roles
