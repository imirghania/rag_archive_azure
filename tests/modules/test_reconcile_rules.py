import pytest

from docai.contracts.enums import TrustTier
from docai.modules.reconcile import decide_line, normalize

KW = dict(min_vote=0.6, from_text_layer=False, printed_floor=0.9)


def test_handwriting_agreement_is_dual_agreed():
    tier, text, cands, _ = decide_line("K. Al Mansoori", 0.83, "K. Al Mansoori", style="handwritten", **KW)
    assert tier is TrustTier.handwritten_dual_agreed and not cands


def test_low_confidence_printed_line_confirmed_by_the_second_reader_stays_printed():
    tier, *_ = decide_line("Total: AED 48,200", 0.82, "Total: AED 48,200", style="printed", **KW)
    assert tier is TrustTier.printed_high_conf


def test_digit_disagreement_is_unverified_with_both_candidates():
    tier, _, cands, _ = decide_line("pay 1,250 by 15/3", 0.71, "pay 1,750 by 15/3", style="handwritten", **KW)
    assert tier is TrustTier.unverified and cands == ["pay 1,250 by 15/3", "pay 1,750 by 15/3"]


def test_ocr_below_vote_threshold_cannot_settle_a_line_even_if_it_matches():
    tier, _, cands, _ = decide_line("يرجى المتابعة", 0.52, "يرجى المتابعة", style="handwritten", **KW)
    assert tier is TrustTier.unverified and cands == ["يرجى المتابعة"]


def test_text_layer_lines_are_digital_source_and_never_second_read():
    tier, *_ = decide_line("Date: 1 May 2008", 0.99, None, style="printed", **{**KW, "from_text_layer": True})
    assert tier is TrustTier.digital_source


@pytest.mark.parametrize("a,b", [("1,750", "١٬٧٥٠"), ("يُرجى", "يرجى"), ("Approved  PAY", "approved pay")])
def test_normalisation_makes_equivalent_readings_equal(a, b):
    assert normalize(a) == normalize(b)


def test_normalisation_keeps_different_digits_different():
    assert normalize("1,750") != normalize("1750") and normalize("1,750") != normalize("1,250")
