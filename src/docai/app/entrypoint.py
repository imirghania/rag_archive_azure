"""The `docai-run` console script, the container command of every job and app."""
from __future__ import annotations

import sys


def run() -> None:
    """`docai-run <module>`: the container command. It avoids `python -m ...`, 
    whose `-m` the Azure CLI would read as its own option."""
    import runpy

    from docai.core import catalog
    from docai.runtime.context import set_context_factory

    from .wiring import build_context

    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in {c.module for c in catalog.COMPONENTS}:
        raise SystemExit(f"unknown module {name!r}; known: {sorted({c.module for c in catalog.COMPONENTS})}")
    set_context_factory(build_context)
    runpy.run_module(f"docai.modules.{name}", run_name="__main__", alter_sys=True)
