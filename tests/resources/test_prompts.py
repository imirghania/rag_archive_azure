import pytest

from docai.resources import prompts
from docai.contracts import llm

NAMES = ["second_reader", "router", "segmentation", "metadata", "agent", "verifier"]


@pytest.mark.parametrize("name", NAMES)
def test_every_prompt_loads_and_is_not_empty(name):
    assert len(prompts.load(name)) > 200


def test_second_reader_prompt_can_never_receive_the_ocr_text():
    # the independence of the second reading depends on this (spec, Workflow 1, Step 5)
    assert prompts.placeholders("second_reader") == {"lang_hint"}
    text = prompts.render("second_reader", lang_hint="ar").lower()
    assert "ocr" not in text


def test_render_fails_loudly_on_a_missing_value():
    with pytest.raises(KeyError):
        prompts.render("second_reader")


def test_prompts_ask_for_the_json_shapes_the_models_parse():
    assert llm.VlmOutput.model_validate({"text": "x", "lang": "ar", "uncertain": []})
    assert llm.RouterOutput.model_validate({"language": "en", "intent": "doc_lookup", "query_en": "q"})
    assert llm.VerifierOutput.model_validate({"verdicts": [{"claim_id": 1, "verdict": "supported"}]})
    for name, needle in [("router", "query_en"), ("segmentation", "verdict"), ("metadata", "evidence"),
                         ("verifier", "verdicts"), ("second_reader", "uncertain")]:
        assert needle in prompts.load(name)


def test_agent_prompt_defines_the_citation_marker_the_verifier_parses():
    assert "[c:<chunk_id>#<page>/<line>]" in prompts.load("agent")
    assert "NO_EVIDENCE" in prompts.load("agent")
