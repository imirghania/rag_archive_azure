"""The values you may edit. Everything else comes from `.env` through docai.core.settings, so the application and the
deployment never disagree about the region, the prefix or the model names."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

from docai.devtools.cli import models
from docai.core.settings import Settings

ROOT = Path(__file__).resolve().parents[1]

# =============================================================================
# Change these as needed. Prefix, environment, region and resource group are read from .env
# (DOCAI_PREFIX, DOCAI_ENV, DOCAI_LOCATION, DOCAI_RESOURCE_GROUP).
# =============================================================================
POSTGRES_TIER = "Burstable"
POSTGRES_SKU = "Standard_B1ms"
POSTGRES_STORAGE_GB = 32
POSTGRES_VERSION = "16"

# =============================================================================
# DON'T CHANGE ANYTHING BELOW THIS LINE.
# =============================================================================


@dataclass(frozen=True)
class Config:
    env_file: Path
    prefix: str
    env: str
    location: str
    resource_group: str
    db_name: str
    subscription_id: str
    tenant_id: str
    models: list[tuple[str, str, str, int]]  # deployment, version, SKU, capacity
    model_env: dict[str, str]  # DOCAI_MODELS__<ROLE> -> deployment, handed to the containers
    raw_retention_days: int
    users: dict[str, str]  # DOCAI_USER_<NAME> -> sign-in name of a test user


def load_config(env_file: Path | None = None) -> Config:
    """Read `.env` (never executed) and the process environment; the process environment wins."""
    env_file = env_file or Path(os.environ.get("DOCAI_ENV_FILE") or ROOT / ".env")
    s = Settings(_env_file=env_file)  # type: ignore[call-arg]  # pydantic-settings init argument
    values = {**dotenv_values(env_file), **os.environ}
    roles = {k: v for k, v in s.models.model_dump().items() if k != "embedding_dimensions"}
    return Config(
        env_file=env_file, prefix=s.prefix, env=s.env, location=s.location, resource_group=s.resource_group,
        db_name=s.database.name, subscription_id=s.azure.subscription_id, tenant_id=s.azure.tenant_id,
        models=models(s), model_env={f"DOCAI_MODELS__{k.upper()}": v for k, v in roles.items()},
        raw_retention_days=int(values.get("DOCAI_RAW_RETENTION_DAYS") or 0),
        users={k: v for k, v in values.items() if k.startswith("DOCAI_USER_") and v},
    )
