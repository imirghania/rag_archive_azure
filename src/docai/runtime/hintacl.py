"""Who may read a published note (spec, Workflow 5, Step 5): only people who may read everything it rests on."""
from __future__ import annotations

import logging
from typing import Any

from docai.contracts import keys

from .context import Context

log = logging.getLogger("docai.hints")


def dossiers_behind(hint: dict[str, Any]) -> set[str]:
    out = set(hint.get("scope_dossier_ids") or [])
    for ev in hint.get("evidence") or []:
        doc_id, _, _ = keys.parse_chunk_id(ev["chunk_id"])
        out.add(keys.parse_document_id(doc_id)[0])
    return out


def hint_audience(ctx: Context, hint: dict[str, Any]) -> list[str]:
    """The intersection of the access groups of every dossier the note cites or is anchored to, 
    read from SQL and not from the index. A note with no documentary evidence (tacit) gets the department's reader groups. A department-wide note whose evidence sits in a treasury-only dossier therefore gets the treasury groups, not all Finance readers."""
    registry = ctx.ops.registered_groups()
    dossiers = dossiers_behind(hint)
    if not dossiers:
        return sorted(g for g, (dept, kind) in registry.items() if dept == hint["department"] and kind == "reader")
    sets = [set(ctx.ops.dossier_acl(d)) for d in dossiers]
    acl = set.intersection(*sets)
    if not acl:
        log.warning("hint %s: the evidence has no common reader group; falling back to the department's stewards", hint["hint_id"])
        acl = {g for g, (dept, kind) in registry.items() if dept == hint["department"] and kind == "steward"}
    return sorted(acl)
