"""Run the whole system on this machine with the local fakes: `uv run python -m docai.devtools.localdev`.

Opens http://localhost:8000 with a development sign-in for the four test users. A background thread plays the part of KEDA
(it drains the queues) and the outbox relay. Needs the sample material: see the README to generate it."""
from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

from starlette.testclient import TestClient

from docai.app.wiring import build_context
from docai.core.settings import Settings
from docai.runtime.context import Context
from docai.security.access import Principal

from . import bootstrap, pg

FIN_READERS, FIN_EXPERTS, FIN_STEWARDS, FIN_TREASURY, HR_READERS, HR_EXPERTS, HR_STEWARDS = (f"{i}" * 8 + "-" + f"{i}" * 4 + "-" + f"{i}" * 4 + "-" + f"{i}" * 4 + "-" + f"{i}" * 12 for i in "1234567")

DEV_USERS = {
    "layla": Principal("aaaaaaaa-0000-0000-0000-00000000000a", "Layla Hassan", ["DocAI.Reader"], [FIN_READERS]),
    "sara": Principal("aaaaaaaa-0000-0000-0000-000000000001", "Sara Aziz", ["DocAI.Expert"], [FIN_READERS, FIN_EXPERTS, FIN_TREASURY]),
    "rana": Principal("aaaaaaaa-0000-0000-0000-000000000002", "Rana Saleh", ["DocAI.Steward"], [FIN_READERS, FIN_STEWARDS, HR_READERS, HR_STEWARDS]),
    "yousef": Principal("aaaaaaaa-0000-0000-0000-000000000004", "Yousef Karim", ["DocAI.Admin"], []),
    "huda": Principal("aaaaaaaa-0000-0000-0000-00000000000b", "Huda (HR)", ["DocAI.Expert"], [HR_READERS, HR_EXPERTS]),
}


def seed_registry(ctx: Context) -> None:
    for code, name in (("FIN", "Finance"), ("HR", "Human Resources")):
        ctx.ops.add_department(code, name)
    for gid, dept, kind, name in [(FIN_READERS, "FIN", "reader", "grp-docai-fin-readers"), (FIN_EXPERTS, "FIN", "expert", "grp-docai-fin-experts"),
                                (FIN_STEWARDS, "FIN", "steward", "grp-docai-fin-stewards"), (FIN_TREASURY, "FIN", "restricted", "grp-docai-fin-treasury"),
                                (HR_READERS, "HR", "reader", "grp-docai-hr-readers"), (HR_EXPERTS, "HR", "expert", "grp-docai-hr-experts"),
                                (HR_STEWARDS, "HR", "steward", "grp-docai-hr-stewards")]:
        ctx.ops.add_access_group(gid, dept, kind, name)


def build_local_web(ctx: Context):
    """app-web wired to the internal apps in this process."""
    from docai.modules import chat_api, review, upload_api, web

    be = web.Backends(chat=TestClient(chat_api.create_app(ctx)), review=TestClient(review.create_app(ctx)), upload=TestClient(upload_api.create_app(ctx)))
    return web.create_app(ctx, be, dev_users=DEV_USERS)


def pump_forever(ctx: Context, interval: float = 1.0) -> None:
    from docai.modules import review
    from docai.runtime.runner import drain

    while True:
        try:
            review.relay_outbox(ctx)
            drain(ctx)
        except Exception:
            import logging
            logging.getLogger("docai.localdev").exception("pump failed")
        time.sleep(interval)


CONTAINER, PORT = "docai-pg-dev", "55432"


def dev_database(keep: bool) -> str:
    """The URL of the dev PostgreSQL: starts the container (or reuses it with --keep). The default URL of Settings points at it."""
    pg.require_docker()
    status = pg.state(CONTAINER)
    if keep and status:
        if status != "running":
            pg._docker("start", CONTAINER)
        return pg.url_of(CONTAINER, "docai", "docai")
    if status:
        pg.stop(CONTAINER)
    return pg.start(CONTAINER, port=PORT, user="docai", db="docai", remove_on_stop=not keep)


def main(argv: list[str] | None = None) -> None:
    import uvicorn

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", action="store_true", help="leave the dev PostgreSQL container running on exit and reuse it next time")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)
    fixtures = Path("samples/out/fixtures")
    if not fixtures.exists():
        raise SystemExit("generate the samples first: uv run python -c \"from pathlib import Path; from docai.devtools.samples import generate; generate(Path('samples/out'))\"")
    settings = Settings(adapters="local", local_fixtures_dir=fixtures)
    own_container = "url" not in settings.database.model_fields_set  # DOCAI_DATABASE__URL (or .env) names the user's own server
    try:
        if own_container:
            settings.database.url = dev_database(args.keep)
        bootstrap.migrate(bootstrap.admin_engine(settings, {}))
        ctx = build_context(settings)
        seed_registry(ctx)
        threading.Thread(target=pump_forever, args=(ctx,), daemon=True).start()
        print("Sample files to upload are in samples/out/dossiers/<dossier id>/ (use dossier ID = the folder name, as Sara).")
        uvicorn.run(build_local_web(ctx), host="127.0.0.1", port=args.port)
    finally:
        if own_container and not args.keep:
            pg.stop(CONTAINER)


if __name__ == "__main__":
    main()
