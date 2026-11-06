import json
import logging

import pytest

from docai.runtime.launch import configure_logging


@pytest.fixture
def configure(monkeypatch):
    """configure_logging() on a bare root logger (pytest's own handlers would make basicConfig a no-op); everything is restored."""
    monkeypatch.delenv("DOCAI_AZURE__APPINSIGHTS_CONNECTION_STRING", raising=False)
    root = logging.getLogger()
    handlers, level, azure_level = root.handlers[:], root.level, logging.getLogger("azure").level

    def run():
        root.handlers.clear()
        configure_logging()
    yield run
    root.handlers[:], root.level = handlers, level
    logging.getLogger("azure").setLevel(azure_level)


def test_sdk_http_logging_is_quiet_while_docai_loggers_keep_the_configured_level(configure):
    configure()
    assert logging.getLogger("azure.core.pipeline.policies.http_logging_policy").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("docai.runtime.launch").isEnabledFor(logging.INFO)


def test_a_record_with_quotes_newlines_and_a_traceback_is_one_valid_json_line(configure, capsys):
    configure()
    try:
        raise ValueError('bad "value"')
    except ValueError:
        logging.getLogger("docai.x").exception('said "hi"\nsecond line')
    lines = capsys.readouterr().out.splitlines()
    rec = json.loads(lines[0])
    assert len(lines) == 1 and rec["level"] == "ERROR" and rec["logger"] == "docai.x"
    assert 'said "hi"\nsecond line' in rec["message"] and "ValueError: bad" in rec["message"]
