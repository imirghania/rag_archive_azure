"""Prompts live in /prompts as text files, so they are reviewed like code and tested like code."""
from __future__ import annotations

import re
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[3] / "prompts"
_PLACEHOLDER = re.compile(r"(?<!\{)\{([a-z_]+)\}(?!\})")


def load(name: str) -> str:
    return (PROMPT_DIR / f"{name}.system.md").read_text(encoding="utf-8")


def placeholders(name: str) -> set[str]:
    return set(_PLACEHOLDER.findall(load(name)))


def render(name: str, **values: str) -> str:
    text = load(name)
    missing = placeholders(name) - values.keys()
    if missing:
        raise KeyError(f"prompt {name} needs {sorted(missing)}")
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    return text
