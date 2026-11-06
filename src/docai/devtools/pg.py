"""A PostgreSQL 16 in a Docker container, for `localdev` and the test suite. Docker is required for both."""
from __future__ import annotations

import shutil
import subprocess
import time

IMAGE = "postgres:16"
NO_DOCKER = ("Docker is needed to run PostgreSQL locally and was not found. Install Docker, or point DOCAI_DATABASE__URL at a PostgreSQL 16 "
             "of your own, for example DOCAI_DATABASE__URL=postgresql+psycopg://user:password@host:5432/dbname (a superuser: the "
             "migrations create roles).")


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True)


def require_docker() -> None:
    if not shutil.which("docker") or _docker("info", check=False).returncode != 0:
        raise SystemExit(NO_DOCKER)


def state(name: str) -> str | None:
    """'running', 'exited', ... or None when no container has this name."""
    r = _docker("inspect", "-f", "{{.State.Status}}", name, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def start(name: str, *, port: str = "", user: str = "postgres", db: str = "postgres", fast: bool = False, remove_on_stop: bool = True) -> str:
    """Starts the container (an empty `port` means a random free one) and returns the superuser URL once the server accepts connections.
    `fast` turns off durability: for throwaway test databases."""
    cmd = ["run", "-d", "--name", name, "-p", f"127.0.0.1:{port}:5432", "-e", f"POSTGRES_USER={user}", "-e", "POSTGRES_PASSWORD=docai", "-e", f"POSTGRES_DB={db}"]
    if remove_on_stop:
        cmd.insert(2, "--rm")
    cmd.append(IMAGE)
    if fast:
        cmd += ["-c", "fsync=off", "-c", "synchronous_commit=off", "-c", "full_page_writes=off"]
    _docker(*cmd)
    try:
        return url_of(name, user, db)
    except BaseException:
        stop(name)
        raise


def url_of(name: str, user: str = "postgres", db: str = "postgres") -> str:
    """The superuser URL of a running container, once it accepts connections."""
    port = _docker("port", name, "5432/tcp").stdout.split(":")[-1].strip()
    url = f"postgresql+psycopg://{user}:docai@127.0.0.1:{port}/{db}"
    wait(url)
    return url


def wait(url: str, timeout: float = 90) -> None:
    import psycopg

    dsn = url.replace("postgresql+psycopg://", "postgresql://")
    end = time.monotonic() + timeout
    while True:
        try:
            psycopg.connect(dsn, connect_timeout=2).close()  # the init-time server listens on the socket only, so TCP means ready
            return
        except psycopg.OperationalError:
            if time.monotonic() > end:
                raise
            time.sleep(0.5)


def stop(name: str) -> None:
    _docker("rm", "-f", name, check=False)
