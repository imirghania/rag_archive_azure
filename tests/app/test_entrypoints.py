"""Every job and app in the catalogue can be started with `python -m docai.modules.<module>`."""
import ast
from pathlib import Path

import pytest

from docai.core import catalog
from docai.app import entrypoint
from docai.runtime.launch import drain_queue
from docai.runtime.runner import load_handlers

MODULES = Path(__file__).resolve().parents[2] / "src" / "docai" / "modules"


@pytest.mark.parametrize("c", catalog.COMPONENTS, ids=lambda c: c.name)
def test_each_component_has_a_module_with_an_entry_point(c):
    src = (MODULES / f"{c.module}.py").read_text()
    assert "if __name__ == \"__main__\":" in src, f"{c.name}: python -m docai.modules.{c.module} would do nothing"
    names = {n.name for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.FunctionDef,))}
    if c.kind == "job" and c.consumes_queue:
        assert "handle" in names
    if c.kind == "job" and c.schedule:
        assert "run" in names
    if c.kind == "app" and not (c.consumes_queue or c.consumes_subscription):
        assert "create_app" in names or c.module == "web"


def test_every_queue_and_subscription_has_a_handler_in_the_registry():
    assert set(load_handlers()) == {c.consumes_queue or c.consumes_subscription for c in catalog.COMPONENTS if c.consumes_queue or c.consumes_subscription}


def test_a_job_execution_ends_when_its_queue_is_empty(ctx):
    from conftest import upload
    upload(ctx, "FIN-C07-S1-F0201")
    n = drain_queue(ctx, "q-intake", load_handlers()["q-intake"])
    assert n == 1 and ctx.queue.depth("q-intake") == 0
    assert drain_queue(ctx, "q-intake", load_handlers()["q-intake"]) == 0


def test_the_container_command_refuses_unknown_modules_and_starts_known_ones(monkeypatch):
    import sys
    from docai.app import entrypoint
    monkeypatch.setattr(sys, "argv", ["docai-run", "nope"])
    with pytest.raises(SystemExit, match="unknown module"):
        entrypoint.run()
    ran = []
    import runpy
    monkeypatch.setattr(runpy, "run_module", lambda name, **kw: ran.append((name, kw["run_name"])))
    monkeypatch.setattr(sys, "argv", ["docai-run", "intake"])
    entrypoint.run()
    assert ran == [("docai.modules.intake", "__main__")]


def test_every_catalogue_command_has_no_leading_dash_for_the_azure_cli():
    from pathlib import Path
    script = (Path(__file__).resolve().parents[2] / "deploy" / "s50_apps.py").read_text()
    assert '"--command", "docai-run", c.module' in script and "python -m" not in script
