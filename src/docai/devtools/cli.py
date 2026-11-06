"""Small helper commands for the deployment scripts and for local setup.

    python -m docai.devtools.cli queues        name|sessions|dup_window|max_delivery
    python -m docai.devtools.cli models        deployment|version|sku|capacity   (unique, from settings)
    python -m docai.devtools.cli components    name|kind|module|queue|subscription|schedule|min|max|msgs|cpu|mem|public|sql_role
    python -m docai.devtools.cli roles NAME    role|scope kind|scope name        (Azure RBAC rows of one component)
    python -m docai.devtools.cli search-def docs|notes
    python -m docai.devtools.cli synonyms      one JSON object per line
"""
from __future__ import annotations

import json
import sys

from docai.contracts.messages import NOTIFY_TYPES, QUEUES, SUBSCRIPTION_NOTIFY
from docai.core import catalog
from docai.core.settings import Settings
from docai.resources import searchdefs

# Known deployable models: version, SKU, capacity (thousands of tokens per minute). Checked against
# `az cognitiveservices model list -l swedencentral` on 2026-11-05.
KNOWN_MODELS = {
    "gpt-5-mini": ("2025-08-07", "GlobalStandard", 100),
    "gpt-5": ("2025-08-07", "GlobalStandard", 50),
    "gpt-4o": ("2024-11-20", "Standard", 50),
    "gpt-4o-mini": ("2024-07-18", "Standard", 100),
    "text-embedding-3-large": ("1", "Standard", 100),
}


def models(settings: Settings) -> list[tuple[str, str, str, int]]:
    seen: dict[str, tuple[str, str, str, int]] = {}
    for role, name in settings.models.model_dump().items():
        if role == "embedding_dimensions":
            continue
        if name not in KNOWN_MODELS:
            raise SystemExit(f"unknown model '{name}' for {role}: add it to KNOWN_MODELS with its version and SKU")
        v, sku, cap = KNOWN_MODELS[name]
        seen.setdefault(name, (name, v, sku, cap))
    return list(seen.values())


def main(argv: list[str]) -> int:
    cmd, *rest = argv or ["help"]
    s = Settings()
    if cmd == "queues":
        for q in QUEUES.values():
            print(f"{q.name}|{str(q.sessions).lower()}|{q.dup_window}|{q.max_delivery}")
    elif cmd == "notify-filter":
        print("type IN (" + ", ".join(f"'{t}'" for t in NOTIFY_TYPES) + ")")
    elif cmd == "models":
        for row in models(s):
            print("|".join(str(x) for x in row))
    elif cmd == "components":
        for c in catalog.COMPONENTS:
            print("|".join(str(x) for x in [c.name, c.kind, c.module, c.consumes_queue or "", c.consumes_subscription or "",
                                            c.schedule or "", c.min_replicas, c.max_executions, c.messages_per_execution,
                                            c.cpu, c.memory, str(c.public).lower(), c.sql_role or ""]))
    elif cmd == "roles":
        for role, kind, name in catalog.role_assignments(catalog.BY_NAME[rest[0]]):
            print(f"{role}|{kind}|{name}")
    elif cmd == "search-def":
        print(json.dumps(searchdefs.index_definition(rest[0], s.models.embedding_dimensions), ensure_ascii=False))
    elif cmd == "synonyms":
        for m in searchdefs.synonym_maps():
            print(json.dumps(m, ensure_ascii=False))
    elif cmd == "subscription":
        print(SUBSCRIPTION_NOTIFY)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
