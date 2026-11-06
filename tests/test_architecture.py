"""Layer rules (spec, How the MVP is built): a package imports only lower layers, modules never import each other,
and the import graph (function-level imports included) has no cycle.
Allowed exception: string-based dynamic imports (importlib, runpy) are invisible to this AST test. The one deliberate
case is docai.runtime.context.new_context, which imports docai.app.wiring by name when no factory is registered, so
`python -m docai.modules.<x>` keeps working."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
SRC = ROOT / "docai"
MODULES = SRC / "modules"
FORBIDDEN_PREFIXES = ("azure", "openai")  # Azure SDKs live in adapters only

ALL = {"contracts", "schemas", "core", "resources", "security", "ports", "db", "documents",
       "adapters", "runtime", "modules", "app", "devtools"}
# package -> packages it may import (itself is always allowed)
ALLOWED = {
    "contracts": set(),
    "schemas": {"contracts"},
    "core": {"contracts"},
    "resources": {"core"},
    "security": {"contracts", "core"},
    "ports": {"contracts", "schemas"},
    "db": {"core"},
    "documents": {"contracts", "ports"},
    "adapters": {"ports", "contracts", "schemas", "core", "security", "db", "resources"},
    "runtime": {"contracts", "schemas", "core", "resources", "security", "ports", "db", "documents"},
    "modules": {"runtime", "ports", "security", "documents", "resources", "contracts", "schemas", "core"},
    "app": ALL,
    "devtools": ALL,
    "deploy": ALL,
}


def _imports(path: Path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            yield node.level, node.module or "", [a.name for a in node.names]
        elif isinstance(node, ast.Import):
            for a in node.names:
                yield 0, a.name, []


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _graph() -> dict[str, set[str]]:
    files = {_module_name(p): p for p in SRC.rglob("*.py")}
    graph: dict[str, set[str]] = {m: set() for m in files}
    for mod, path in files.items():
        pkg = mod.split(".") if path.name == "__init__.py" else mod.split(".")[:-1]
        for level, name, names in _imports(path):
            base = ".".join(pkg[: len(pkg) - level + 1]) if level else ""
            target = ".".join(x for x in (base, name) if x)
            subs = [f"{target}.{n}" for n in names if f"{target}.{n}" in files]  # `from x import y` where y is a module
            for cand in subs or [target]:
                if cand in files and cand != "docai" and cand != mod:
                    graph[mod].add(cand)
    return graph


def _package(mod: str) -> str:
    return mod.split(".")[1]


def _violations(graph) -> set[tuple[str, str]]:
    bad = set()
    for a, targets in graph.items():
        if a == "docai":
            continue
        for b in targets:
            pa, pb = _package(a), _package(b)
            assert pa in ALLOWED, f"{a}: package {pa} is not in the layer table"
            assert pb in ALLOWED, f"{b}: package {pb} is not in the layer table"
            if pa != pb and pb not in ALLOWED[pa]:
                bad.add((a, b))
    return bad


def _cycles(graph) -> list[list[str]]:  # Tarjan strongly connected components
    index, low, stack, on, out, n = {}, {}, [], set(), [], [0]

    def visit(v):
        index[v] = low[v] = n[0]
        n[0] += 1
        stack.append(v)
        on.add(v)
        for w in graph[v]:
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    for v in graph:
        if v not in index:
            visit(v)
    return out


def test_imports_follow_the_layer_table():
    found = _violations(_graph())
    assert not found, f"layer violations: {sorted(found)}"


def test_import_graph_has_no_cycle():
    assert not _cycles(_graph()), f"import cycles: {_cycles(_graph())}"


def test_no_module_imports_a_sibling_module():
    siblings = {p.stem for p in MODULES.glob("*.py")} - {"__init__"}
    for f in MODULES.glob("*.py"):
        for level, mod, names in _imports(f):
            if level == 1:  # `from .other import x` or `from . import other`
                target = mod.split(".")[0] if mod else None
                assert target not in siblings, f"{f.name} imports sibling module {target}"
                if not mod:
                    assert not set(names) & siblings, f"{f.name} imports sibling modules {names}"
            if level == 0 and mod.startswith("docai.modules"):
                raise AssertionError(f"{f.name} imports {mod}")


def test_modules_use_ports_not_azure_sdks():
    for f in MODULES.glob("*.py"):
        for level, mod, _ in _imports(f):
            assert level != 0 or not mod.split(".")[0] in FORBIDDEN_PREFIXES, f"{f.name} imports the SDK {mod}"
            assert "adapters" not in mod, f"{f.name} imports an adapter directly"


def test_relative_imports_stay_inside_their_package():
    # Across packages imports are absolute (`from docai.ports import X`). adapters/azure, local and sql count as
    # one package, so `from ..x` may climb from adapters/<sub> to adapters but never further.
    for f in SRC.rglob("*.py"):
        rel = f.relative_to(SRC)
        subdirs = len(rel.parts) - 2  # directories below the top-level package that holds the file
        for level, mod, _ in _imports(f):
            assert level == 0 or (len(rel.parts) > 1 and level - 1 <= subdirs), (
                f"{rel}: relative import climbs out of its package ({'.' * level}{mod})")
