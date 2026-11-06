"""Loads the search index definitions from /search and fills in the placeholders.

The JSON files are the single source of truth for the index shape. The bootstrap script and the
Azure adapter both load them here, so they can never disagree with the tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SEARCH_DIR = Path(__file__).resolve().parents[3] / "search"
API_VERSION = "2024-07-01"  # GA: scalar quantization, semantic ranker. Aliases need a preview version (2025-05-01-preview) and cannot be queried with this one, so they are not used (D48)


def _load(name: str) -> Any:
    return json.loads((SEARCH_DIR / name).read_text(encoding="utf-8"))


def index_definition(which: str, dimensions: int) -> dict[str, Any]:
    """`which` is `docs` or `notes`. Vector fields get the configured dimension."""
    text = json.dumps(_load(f"{which}.index.json"))
    return json.loads(text.replace('"__DIMS__"', str(dimensions)))


def synonym_maps() -> list[dict[str, Any]]:
    return [_load("en-synonyms.json"), _load("ar-synonyms.json")]


def index_name(which: str) -> str:
    """The index behind the logical name `docs` or `notes` (the callers and the adapter use the logical names): `docs-v1`, `notes-v1`."""
    return _load(f"{which}.index.json")["name"]


def field_names(defn: dict[str, Any]) -> set[str]:
    return {f["name"] for f in defn["fields"]}
