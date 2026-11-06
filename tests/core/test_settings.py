from docai.core.settings import Settings


def test_defaults_map_every_role_to_a_deployment():
    s = Settings(_env_file=None)
    assert s.adapters == "local"
    assert s.models.router == "gpt-5-mini"
    assert s.models.embeddings == "text-embedding-3-large"


def test_env_overrides_nested_values(monkeypatch):
    monkeypatch.setenv("DOCAI_MODELS__SECOND_READER", "gpt-5")
    monkeypatch.setenv("DOCAI_LOCATION", "eastus2")
    monkeypatch.setenv("DOCAI_TUNING__CHUNK_MAX_TOKENS", "300")
    s = Settings(_env_file=None)
    assert s.models.second_reader == "gpt-5"
    assert s.location == "eastus2"
    assert s.tuning.chunk_max_tokens == 300


def test_the_database_defaults_to_the_local_dev_postgres_and_builds_the_azure_url_from_parts(monkeypatch):
    assert Settings(_env_file=None).database.sqlalchemy_url == "postgresql+psycopg://docai:docai@localhost:55432/docai"
    monkeypatch.setenv("DOCAI_DATABASE__HOST", "pg.postgres.database.azure.com")
    monkeypatch.setenv("DOCAI_DATABASE__USER", "id-job-intake")
    monkeypatch.setenv("DOCAI_DATABASE__ENTRA_AUTH", "true")
    d = Settings(_env_file=None).database
    assert d.entra_auth and d.sqlalchemy_url == "postgresql+psycopg://id-job-intake@pg.postgres.database.azure.com:5432/docai"
