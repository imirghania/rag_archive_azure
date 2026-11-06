"""Shared pieces of the deployment steps: the one place that runs `az`, the state file, the derived names.

Dry run: `Az` never starts a process. `run` records and prints the command, `query` returns its placeholder, `exists`
is False. Steps therefore need no `if dry_run` branches; values produced by an earlier command are placeholders."""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from docai.contracts.messages import TOPIC
from docai.core import catalog

from .config import ROOT, Config, load_config

ZERO_GUID = "00000000-0000-0000-0000-000000000000"
ID_NAMESPACE = uuid.UUID("6f1d2c8a-5e1b-4a7e-9d3c-0b1a2c3d4e5f")  # fixed, so a rerun never creates a second role ID

_EXE_CACHE: dict[str, str] = {}


class DeployError(Exception):
    """A step cannot continue; the message tells the person what to do."""


def say(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _resolve_exe(name: str) -> str:
    """Locate an executable on PATH, including Windows command wrappers."""
    if name not in _EXE_CACHE:
        found = shutil.which(name)
        if not found:
            raise DeployError(f"'{name}' not found on PATH. Install it and retry.")
        _EXE_CACHE[name] = found
    return _EXE_CACHE[name]


def stable_id(name: str) -> str:
    """Deterministic uuid5: the ID of an app role or scope depends only on its name."""
    return str(uuid.uuid5(ID_NAMESPACE, name))


def key_of(component: str) -> str:
    return component.replace("-", "_")


def _with_query(argv: list[str], jmes: str | None, out: str = "tsv") -> list[str]:
    return [*argv, "--query", jmes, "-o", out] if jmes else list(argv)


class Az:
    """Every Azure CLI call of the deployment goes through `_exec`; in dry run nothing reaches it."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.commands: list[list[str]] = []  # every mutating command so far, as ["az", ...]
        os.environ.setdefault("AZURE_CORE_ONLY_SHOW_ERRORS", "true")

    def _exec(self, argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run([_resolve_exe("az"), *argv], capture_output=True, text=True, check=False)

    def run(self, argv: list[str], *, query: str | None = None, placeholder: str = "", check: bool = True,
            retries: int = 1, wait: int = 0) -> str:
        """Run a command that changes something and return its output (the placeholder in dry run).
        With `check=False` a failure returns ''. `retries` x `wait` seconds covers role assignments that apply late."""
        argv = _with_query(argv, query)
        self.commands.append(["az", *argv])
        if self.dry_run:
            say("[dry-run] " + shlex.join(["az", *argv]))
            return placeholder
        say("[az] " + " ".join(argv[:3]))  # only the first words: later ones may be a secret
        for attempt in range(1, retries + 1):
            r = self._exec(argv)
            if r.returncode == 0:
                return _none_is_empty(r.stdout)
            if attempt < retries:
                say(f"  failed, retrying in {wait}s ({attempt}/{retries})")
                time.sleep(wait)
        if check:
            raise DeployError(f"az {' '.join(argv[:3])} failed (exit {r.returncode}):\n{(r.stdout + r.stderr).strip()}")
        return ""

    def query(self, argv: list[str], jmes: str | None = None, placeholder: str = "", out: str = "tsv") -> str:
        """A read-only probe. '' when it fails or finds nothing; the placeholder in dry run."""
        if self.dry_run:
            return placeholder
        r = self._exec(_with_query(argv, jmes, out))
        return _none_is_empty(r.stdout) if r.returncode == 0 else ""

    def exists(self, show: list[str]) -> bool:
        """True when a `show` command succeeds. Always False in dry run, so every create is planned."""
        return not self.dry_run and self._exec([*show, "-o", "none"]).returncode == 0

    def ensure(self, show: list[str], create: list[str]) -> bool:
        """Create only when `show` fails; returns True when it created."""
        if self.exists(show):
            return False
        self.run(create)
        return True

    def rest(self, method: str, url: str, body: dict | list | None = None, *, query: str | None = None,
             placeholder: str = "") -> str:
        argv = ["rest", "--method", method, "--url", url] + (["--body", json.dumps(body)] if body is not None else [])
        if method == "get":
            return self.query(argv, query, placeholder)
        return self.run(argv, query=query, placeholder=placeholder)

    def rest_exists(self, url: str) -> bool:
        return self.exists(["rest", "--method", "get", "--url", url])

    def wait(self, probe: list[str], jmes: str, want: str, tries: int, delay: int) -> bool:
        """Poll a probe until it prints `want`. Dry run does not wait."""
        for _ in range(tries):
            if self.dry_run or self.query(probe, jmes) == want:
                return True
            time.sleep(delay)
        return False

    def signed_in(self) -> bool:
        return self.dry_run or self.exists(["account", "show"])


def _none_is_empty(text: str) -> str:
    text = text.strip()
    return "" if text == "None" else text  # `-o tsv` prints None for null


class State:
    """Names and IDs produced by the steps (not secrets), as JSON. A dry run has its own file, so placeholders never leak."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}

    def get(self, key: str, default: str = "") -> str:
        return self.data.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.path)

    def delete(self) -> None:
        self.path.unlink(missing_ok=True)
        self.data = {}


@dataclass(frozen=True)
class Names:
    """Resource names, derived from the subscription, prefix and environment only: a rerun finds what the last run made."""

    suffix: str
    rg: str
    loc: str
    law: str
    appi: str
    acr: str
    kv: str
    cae: str
    st_raw: str
    st_proc: str
    st_stg: str
    sbns: str
    pg: str
    search: str
    ais: str
    project: str
    topic: str

    @classmethod
    def derive(cls, cfg: Config, sub_id: str) -> Names:
        p = cfg.prefix
        suffix = hashlib.sha1(f"{sub_id}-{p}-{cfg.env}".encode()).hexdigest()[:5]  # 5 characters keep global names stable
        n = cls(
            suffix=suffix, rg=cfg.resource_group, loc=cfg.location, law=f"log-{p}-{cfg.env}", appi=f"appi-{p}-{cfg.env}",
            acr=f"acr{p}{suffix}", kv=f"kv-{p}-{suffix}", cae=f"cae-{p}-{cfg.env}",
            st_raw=f"st{p}raw{suffix}", st_proc=f"st{p}proc{suffix}", st_stg=f"st{p}stg{suffix}",
            sbns=f"sbns-{p}-{suffix}", pg=f"pg-{p}-{suffix}", search=f"srch-{p}-{suffix}", ais=f"ais-{p}-{suffix}",
            project=f"proj-{p}", topic=TOPIC,
        )
        for name in (n.kv, n.st_raw, n.st_proc, n.st_stg, n.acr):  # fail early instead of halfway through
            if len(name) > 24:
                raise DeployError(f"name '{name}' is longer than 24 characters: use a shorter DOCAI_PREFIX")
        return n

    @property
    def sb_fqdn(self) -> str:
        return f"{self.sbns}.servicebus.windows.net"

    @property
    def pg_host(self) -> str:
        return f"{self.pg}.postgres.database.azure.com"

    def account_of(self, container: str) -> str:
        return {"raw": self.st_raw, "proc": self.st_proc, "staging": self.st_stg}[catalog.CONTAINERS[container]]


@dataclass
class Ctx:
    az: Az
    state: State
    cfg: Config
    n: Names
    sub_id: str
    tenant_id: str
    yes: bool = False
    step: str = field(default="deploy")

    def log(self, msg: str) -> None:
        say(f"[{self.step}] {msg}")

    def warn(self, msg: str) -> None:
        say(f"[warn] {msg}")

    def scope(self, provider_path: str = "") -> str:
        """ARM ID of the resource group, or of a resource below it (`Microsoft.KeyVault/vaults/<name>`)."""
        rg = f"/subscriptions/{self.sub_id}/resourceGroups/{self.n.rg}"
        return f"{rg}/providers/{provider_path}" if provider_path else rg

    def need(self, key: str) -> str:
        """A value an earlier step recorded. A dry run that skipped that step gets a placeholder instead of an error."""
        value = self.state.get(key)
        if value:
            return value
        if self.az.dry_run:
            return f"<{key}>"
        raise DeployError(f"'{key}' is not in {self.state.path.name}: run the step that records it first")

    def role(self, oid: str, role: str, scope: str, principal: str = "ServicePrincipal") -> None:
        """Assign a role once. The object ID with an explicit type avoids 'principal not found' while a new identity replicates."""
        if self.az.query(["role", "assignment", "list", "--assignee", oid, "--role", role, "--scope", scope], "[0].id"):
            return
        self.az.run(["role", "assignment", "create", "--assignee-object-id", oid, "--assignee-principal-type", principal,
                     "--role", role, "--scope", scope])

    def public_ip(self) -> str:
        """The address of this machine, for the database firewall; '' when it cannot be found."""
        if self.az.dry_run:
            return "<deployer-ip>"
        try:
            return urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
        except OSError:
            return ""


def git_short_sha() -> str:
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False)
        return r.stdout.strip() or "dev"
    except OSError:  # no git installed: the tag still has a timestamp
        return "dev"


def make_ctx(dry_run: bool = False, yes: bool = False, az: Az | None = None, env_file: Path | None = None) -> Ctx:
    cfg = load_config(env_file)
    az = az or Az(dry_run)
    sub = cfg.subscription_id or az.query(["account", "show"], "id", ZERO_GUID) or ZERO_GUID
    tenant = cfg.tenant_id or az.query(["account", "show"], "tenantId", ZERO_GUID) or ZERO_GUID
    state = State(ROOT / ".local" / ("deploy.dryrun.json" if az.dry_run else "deploy.json"))
    return Ctx(az, state, cfg, Names.derive(cfg, sub), sub, tenant, yes)
