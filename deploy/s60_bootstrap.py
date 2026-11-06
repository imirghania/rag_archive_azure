"""Database migrations, the database users of the identities, department registry, settings, Search indexes, the Foundry agent.
Needs `az login` as the PostgreSQL Entra administrator (the identity that ran step 20): the token is the database password."""
from __future__ import annotations

import os
import subprocess
import sys

from .config import ROOT
from .lib import Ctx


def run(ctx: Ctx) -> None:
    admin = ctx.need("DB_ADMIN")
    cmd = [sys.executable, "-m", "docai.devtools.bootstrap", "all", "--user", admin]
    if ctx.az.dry_run:
        ctx.log("[dry-run] would run: python " + " ".join(cmd[1:]))
        return
    env = {**os.environ, "DOCAI_DATABASE__HOST": ctx.need("DB_HOST"), "DOCAI_DATABASE__NAME": ctx.cfg.db_name,
           "DOCAI_DATABASE__ENTRA_AUTH": "true", "DOCAI_AZURE__SEARCH_ENDPOINT": ctx.need("SEARCH_ENDPOINT")}
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)
