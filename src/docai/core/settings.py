"""All configuration of the application, read from environment variables and a .env file.

Variables carry the prefix DOCAI_ and nested names use a double underscore, for example
DOCAI_MODELS__ROUTER=gpt-5-mini. Nothing in the code names a model deployment or a region:
it asks this class (or the `Settings` port, which wraps it) for the value.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Models(BaseModel):
    """One deployment name per role. Change one value to move a role to another model."""

    answer_agent: str = "gpt-5-mini"
    router: str = "gpt-5-mini"
    segmentation: str = "gpt-5-mini"
    metadata: str = "gpt-5-mini"
    second_reader: str = "gpt-5-mini"
    verifier: str = "gpt-5-mini"
    embeddings: str = "text-embedding-3-large"
    embedding_dimensions: int = 1024  # the index and the Parquet files use this size


class AzureEndpoints(BaseModel):
    subscription_id: str = ""
    tenant_id: str = ""
    servicebus_namespace: str = ""  # <name>.servicebus.windows.net
    storage_raw_account: str = ""
    storage_proc_account: str = ""
    storage_staging_account: str = ""
    search_endpoint: str = ""
    foundry_endpoint: str = ""
    foundry_project_endpoint: str = ""  # https://<account>.services.ai.azure.com/api/projects/<project>
    ocr_endpoint: str = ""
    content_safety_endpoint: str = ""
    key_vault_uri: str = ""
    appinsights_connection_string: str = ""


class Database(BaseModel):
    """The operational database (PostgreSQL). Locally `url` is used as it is. In Azure set `entra_auth` and `host`, `name`, `user`
    (the managed identity's name): the connection then gets an Entra token as its password and requires TLS (docai.db.engine)."""
    url: str = "postgresql+psycopg://docai:docai@localhost:55432/docai"
    host: str = ""  # <server>.postgres.database.azure.com
    name: str = "docai"
    user: str = ""
    entra_auth: bool = False

    @property
    def sqlalchemy_url(self) -> str:
        if not self.entra_auth:
            return self.url
        from sqlalchemy.engine import URL

        return URL.create("postgresql+psycopg", username=self.user, host=self.host, port=5432, database=self.name).render_as_string(hide_password=False)


class Auth(BaseModel):
    tenant_id: str = ""
    api_client_id: str = ""
    web_client_id: str = ""
    web_client_secret: str = ""
    dev_signing_key: str = "dev-only-signing-key-not-a-secret-0123456789"  # signs the local test tokens only


class Services(BaseModel):
    """Internal addresses of the apps behind app-web. In Container Apps an internal app answers on its own name."""

    retrieval_url: str = "http://app-retrieval"
    verifier_url: str = "http://app-verifier"
    chat_url: str = "http://app-chat-api"
    review_url: str = "http://app-review"
    upload_url: str = "http://app-upload-api"


class Tuning(BaseModel):
    """Thresholds and limits. In Azure they can be overridden by rows in ops.settings."""

    # Triage and reconciliation (spec, Workflow 1, Steps 4 and 6)
    printed_second_read_below: float = 0.90
    reconcile_rule_set: int = 1
    reconcile_ocr_min_vote: float = 0.6
    crop_margin_ratio: float = 0.15
    # Chunking (Step 9)
    chunk_max_tokens: int = 500
    # Upload (Workflow 9)
    upload_max_file_mb: int = 500
    upload_max_pages: int = 3000
    upload_block_kb: int = 4096  # 4 MB
    upload_scan_mode: Literal["stub", "defender"] = "stub"  # stub: every file is reported clean
    upload_scan_max_attempts: int = 30  # one a minute: about 30 minutes
    upload_scan_retry_seconds: int = 60
    upload_expire_days: int = 3
    bulk_max_files: int = 200
    bulk_max_pages: int = 5000
    upload_allowed_types: tuple[str, ...] = ("tif", "tiff", "pdf", "doc", "docx", "txt")
    # Review (Workflow 4)
    review_lease_minutes: int = 15
    review_escalate_after_abandons: int = 3
    review_oldest_every_nth_claim: int = 5
    review_demand_window_days: int = 30
    # Operations (Failures)
    watchdog_page_stuck_minutes: int = 30
    watchdog_max_resends: int = 3
    conversations_retention_days: int = 90
    # Answering (Workflow 6)
    search_top: int = 8
    search_vector_k: int = 50


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DOCAI_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    adapters: Literal["local", "azure"] = "local"
    env: str = "dev"

    ocr_engine: Literal["document_intelligence", "content_understanding"] = "document_intelligence"
    local_fixtures_dir: Path = Path("samples/out/fixtures")

    location: str = "swedencentral"
    location_fallback: str = "eastus2"
    prefix: str = "docai"
    resource_group: str = "rg-docai-dev"

    models: Models = Field(default_factory=Models)
    azure: AzureEndpoints = Field(default_factory=AzureEndpoints)
    auth: Auth = Field(default_factory=Auth)
    tuning: Tuning = Field(default_factory=Tuning)
    services: Services = Field(default_factory=Services)
    session_secret: str = "dev-only-session-secret-change-me-0123456789"  # signs the cookie; in Azure it comes from Key Vault
    web_redirect_url: str = "http://localhost:8000/auth/callback"

    local_dir: Path = Path(".local")

    database: Database = Field(default_factory=Database)


@lru_cache
def get_settings() -> Settings:
    return Settings()
