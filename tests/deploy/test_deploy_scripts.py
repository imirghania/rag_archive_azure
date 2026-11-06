"""The deployment (`python -m deploy`), dry-run in-process: `Az` records every command it would run and never starts a process,
so this needs no Azure account. The test fails if anything tries to execute `az`."""
from __future__ import annotations

import dataclasses
import importlib
import itertools
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from deploy import STEPS, select
from deploy.__main__ import run_steps
from deploy.lib import Az, DeployError, State, make_ctx

ROOT = Path(__file__).resolve().parents[2]
REAL_STATE = ROOT / ".local" / "deploy.json"
DRY_STATE = ROOT / ".local" / "deploy.dryrun.json"


@pytest.fixture(scope="module")
def plan(tmp_path_factory):
    """Runs steps 0 to 90 once with a recording Az; yields (ctx, commands, text, env_file)."""
    env_file = tmp_path_factory.mktemp("dry") / "env"
    env_file.write_text((ROOT / ".env.example").read_text())
    real_state_before = REAL_STATE.read_bytes() if REAL_STATE.exists() else None
    DRY_STATE.unlink(missing_ok=True)  # an earlier run's placeholders must not hide a bug

    real_run = subprocess.run

    def no_az(argv, *a, **k):
        assert Path(argv[0]).name not in ("az", "az.cmd", "az.exe"), f"az was executed: {argv}"
        return real_run(argv, *a, **k)

    def no_exec(self, argv):
        raise AssertionError(f"az was executed: {argv}")

    mp = pytest.MonkeyPatch()
    mp.setattr(subprocess, "run", no_az)
    mp.setattr(Az, "_exec", no_exec)
    mp.setenv("DOCAI_USER_SARA", "sara@example.com")
    mp.setenv("IMAGE_TAG", "test")
    ctx = make_ctx(az=Az(dry_run=True), env_file=env_file)
    run_steps(ctx, select())
    mp.undo()
    commands = ctx.az.commands
    yield ctx, commands, "\n".join(shlex.join(c) for c in commands), env_file, real_state_before


def cmds(commands, *prefix):
    return [c for c in commands if c[1:1 + len(prefix)] == list(prefix)]


def test_every_step_module_imports_and_has_run():
    for name in STEPS.values():
        assert callable(importlib.import_module(f"deploy.{name}").run)


def test_steps_are_ordered_and_teardown_is_never_in_the_default_run():
    assert select() == [0, 10, 20, 30, 40, 41, 42, 50, 60, 90]
    assert select(from_=20, to=41) == [20, 30, 40, 41]
    assert select(only=50) == [50] and select(from_=50, to=0) == []
    assert select(from_=0, to=99) == select(), "a range never reaches 99"
    assert select(only=99) == [] and select(teardown=True) == [99]


def test_the_plan_creates_what_the_design_lists(plan):
    _, c, text, *_ = plan
    assert len(cmds(c, "servicebus", "queue", "create")) == 13 and len(cmds(c, "servicebus", "topic", "create")) == 1
    assert len(cmds(c, "containerapp", "job", "create")) == 13 and len(cmds(c, "containerapp", "create")) == 8
    puts = [x for x in cmds(c, "rest", "--method", "put")]
    assert any("/projects/proj-docai?api-version=2025-04-01-preview" in " ".join(x) for x in puts), "the Foundry project is an ARM PUT"
    assert len(puts) == 2, "the account and the project"
    assert len(cmds(c, "identity", "create")) == 21 and "az keyvault secret set" in text
    assert "web-client-secret" in text and "web-session-secret" in text and len(cmds(c, "ad", "group", "create")) == 5


def test_containers_start_through_the_console_script_with_the_right_replicas(plan):
    _, c, *_ = plan
    creates = cmds(c, "containerapp", "job", "create") + cmds(c, "containerapp", "create")
    for cmd in creates:
        i = cmd.index("--command")
        assert cmd[i + 1] == "docai-run" and not cmd[i + 2].startswith("-") and len(cmd) == i + 3
        assert "python" not in cmd and "-m" not in cmd
    app = {x[x.index("-n") + 1]: x for x in cmds(c, "containerapp", "create")}
    assert app["app-review"][app["app-review"].index("--min-replicas") + 1] == "1", "the outbox relay never scales to zero"
    assert app["app-web"][app["app-web"].index("--min-replicas") + 1] == "1"
    assert app["app-verifier"][app["app-verifier"].index("--min-replicas") + 1] == "0"
    assert all("--scale-rule-identity" in x for x in cmds(c, "containerapp", "job", "create") if "Event" in x)
    insecure = {x[x.index("-n") + 1] for x in cmds(c, "containerapp", "ingress", "update")}
    assert insecure == {"app-upload-api", "app-chat-api", "app-retrieval", "app-verifier", "app-review"}


def test_the_database_is_postgres_with_entra_only_authentication(plan):
    ctx, c, text, *_ = plan
    [create] = cmds(c, "postgres", "flexible-server", "create")
    flags = dict(itertools.pairwise(create))
    assert flags["--microsoft-entra-auth"] == "Enabled" and flags["--password-auth"] == "Disabled"
    assert flags["--tier"] == "Burstable" and flags["--sku-name"] == "Standard_B1ms" and flags["--version"] == "16"
    assert flags["--public-access"] == "0.0.0.0" and "--admin-password" not in create
    [admin] = cmds(c, "postgres", "flexible-server", "microsoft-entra-admin", "create")
    assert "-u" in admin and "-i" in admin and "User" in admin
    assert cmds(c, "postgres", "flexible-server", "db", "create")[0][-2:] == ["-d", "docai"]
    assert not cmds(c, "sql") and "database.windows.net" not in text and "SQL_SERVER" not in text and "SQL_DATABASE" not in text
    intake = next(x for x in cmds(c, "containerapp", "job", "create") if "job-intake" in x)
    env = intake[intake.index("--env-vars") + 1:intake.index("--command")]
    assert f"DOCAI_DATABASE__HOST={ctx.n.pg_host}" in env and "DOCAI_DATABASE__USER=id-job-intake" in env
    assert "DOCAI_DATABASE__ENTRA_AUTH=true" in env and "DOCAI_DATABASE__NAME=docai" in env


def test_state_has_an_object_id_for_every_identity_and_the_database_keys(plan):
    ctx, *_ = plan
    from docai.core import catalog

    state = State(DRY_STATE).data
    assert all(f"OID_{c.name.replace('-', '_')}" in state for c in catalog.COMPONENTS)
    assert state["DB_HOST"] == ctx.n.pg_host and state["DB_NAME"] == "docai" and state["DB_ADMIN"]
    assert ctx.state.path == DRY_STATE


def test_no_command_carries_an_unresolved_value(plan):
    _, c, text, *_ = plan
    assert all(arg and arg != "None" and "$(" not in arg and "${" not in arg for cmd in c for arg in cmd)
    assert set(re.findall(r"<[A-Za-z_]+>", text)) <= {"<deployer-ip>"}, "only the dry-run placeholder of the machine's address"
    assert text.index("provider register") < text.index("group create") < text.index("postgres flexible-server create") < text.index("containerapp job create")


def test_users_are_assigned_through_graph_with_deterministic_ids(plan):
    _, c, *_ = plan
    posts = [x for x in cmds(c, "rest", "--method", "post") if "appRoleAssignments" in " ".join(x)]
    assert len(posts) == 2, "sara: the API role and the sign-in app"
    from deploy.lib import stable_id

    assert stable_id("DocAI.Expert") in " ".join(posts[0])
    assert stable_id("DocAI.Expert") == "bc6242ee-ee9d-5cdf-9895-c267178caabf", "the role IDs of the bash version are kept"


def test_a_dry_run_touches_neither_the_real_state_nor_env_file(plan):
    _, _, _, env_file, real_state_before = plan
    assert DRY_STATE.exists()
    assert (REAL_STATE.read_bytes() if REAL_STATE.exists() else None) == real_state_before
    assert env_file.read_text() == (ROOT / ".env.example").read_text() and not env_file.with_name("env.bak").exists()


def test_teardown_asks_for_the_resource_group_name(plan, tmp_path):
    ctx, *_ = plan
    ctx = dataclasses.replace(ctx, state=State(tmp_path / "s.json"))
    real = dataclasses.replace(ctx, az=Az(dry_run=False))  # its _exec is never reached: the confirmation fails first
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("builtins.input", lambda _: "something else")
        with pytest.raises(DeployError, match="not confirmed"):
            importlib.import_module("deploy.s99_teardown").run(real)
    dry = dataclasses.replace(ctx, az=Az(dry_run=True))
    importlib.import_module("deploy.s99_teardown").run(dry)
    assert cmds(dry.az.commands, "keyvault", "purge")


def test_step_90_writes_env_with_a_backup(tmp_path):
    env = tmp_path / ".env"
    env.write_text("DOCAI_ADAPTERS=local\nDOCAI_DATABASE__HOST=\n")
    ctx = make_ctx(az=Az(dry_run=True), env_file=env)
    state = State(tmp_path / "deploy.json")
    state.set("DB_HOST", "pg-x.postgres.database.azure.com")
    state.set("DB_NAME", "docai")
    state.set("DB_ADMIN", "me@example.com")
    importlib.import_module("deploy.s90_write_env").run(dataclasses.replace(ctx, az=Az(dry_run=False), state=state))
    text = env.read_text()
    assert "DOCAI_DATABASE__HOST=pg-x.postgres.database.azure.com" in text and "DOCAI_DATABASE__USER=me@example.com" in text
    assert "DOCAI_DATABASE__ENTRA_AUTH=true" in text and "DOCAI_ADAPTERS=local" in text and text.count("DOCAI_DATABASE__HOST") == 1
    assert (tmp_path / ".env.bak").read_text() == "DOCAI_ADAPTERS=local\nDOCAI_DATABASE__HOST=\n"


def test_az_run_raises_on_failure_and_retries_and_treats_none_as_empty():
    calls = []

    class Fake(Az):
        def _exec(self, argv):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 1 if len(calls) < 3 else 0, "None\n", "boom")

    az = Fake()
    assert az.run(["x"], retries=3, wait=0) == "" and len(calls) == 3
    calls.clear()
    with pytest.raises(DeployError, match="boom"):
        az.run(["x"], retries=1)
    assert az.run(["x"], check=False) == "" and az.query(["x"], "id") == ""


def test_python_m_deploy_dry_run_exits_zero():
    r = subprocess.run([sys.executable, "-m", "deploy", "--dry-run", "--to", "90"], cwd=ROOT, capture_output=True, text=True, timeout=180, check=False)
    assert r.returncode == 0, r.stderr[-1500:]
    assert "=== 90 s90_write_env" in r.stderr and "az postgres flexible-server create" in r.stderr
    refused = subprocess.run([sys.executable, "-m", "deploy", "--dry-run", "--only", "99"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert refused.returncode == 2, "step 99 needs --teardown"


def test_a_component_is_deployed_again_after_the_transient_extension_crash(monkeypatch):
    """The containerapp extension sometimes dies with "unexpected error" on a read call (D49); other errors still stop the step."""
    from deploy import s50_apps
    from deploy.lib import DeployError

    class Ctx:
        warnings: list[str] = []

        def warn(self, msg):
            self.warnings.append(msg)

    monkeypatch.setattr(s50_apps.time, "sleep", lambda s: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise DeployError("az containerapp create failed (exit 1):\nERROR: The command failed with an unexpected error.")

    s50_apps._retrying(Ctx(), "app-verifier", flaky)
    assert len(calls) == 3

    calls.clear()

    def real_error():
        calls.append(1)
        raise DeployError("az containerapp create failed (exit 1):\nERROR: (InvalidParameter) bad value")

    with pytest.raises(DeployError):
        s50_apps._retrying(Ctx(), "app-verifier", real_error)
    assert len(calls) == 1, "a real error is not retried"

    calls.clear()

    def always():
        calls.append(1)
        raise DeployError("ERROR: The command failed with an unexpected error.")

    with pytest.raises(DeployError):
        s50_apps._retrying(Ctx(), "app-verifier", always, tries=3)
    assert len(calls) == 3
