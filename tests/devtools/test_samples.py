import json

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from docai.devtools.samples import generate  # noqa: E402


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    out = tmp_path_factory.mktemp("samples")
    return out, generate(out)


def test_memo_page_has_the_three_handwritten_lines_of_the_spec(samples):
    out, expected = samples
    page5 = expected["dossiers"]["FIN-C03-S2-F0117"]["pages"][4]
    hand = [ln for ln in page5["lines"] if ln["style"] == "handwritten"]
    assert [ln["tier"] for ln in hand] == ["unverified", "handwritten_dual_agreed", "unverified"]
    ocr = json.loads((out / "fixtures/FIN-C03-S2-F0117/p005.ocr.json").read_text())
    texts = {ln["text"] for ln in ocr["lines"]}
    assert "Approved, pay 1,250 by 15/3" in texts  # the OCR error that the second reader must catch
    vlm = json.loads((out / "fixtures/FIN-C03-S2-F0117/p005.vlm.json").read_text())
    assert any(v["text"] == "Approved, pay 1,750 by 15/3" for v in vlm.values())


def test_every_line_box_stays_inside_the_page(samples):
    out, _ = samples
    for f in (out / "fixtures").rglob("*.ocr.json"):
        data = json.loads(f.read_text())
        for ln in data["lines"]:
            b = ln["box"]
            assert 0 <= b["x0"] < b["x1"] <= data["page_width"], (f, ln["id"])
            assert 0 <= b["y0"] < b["y1"] <= data["page_height"], (f, ln["id"])


def test_manifest_hashes_match_the_files(samples):
    import hashlib
    out, _ = samples
    for m in (out / "dossiers").glob("*/dossier.json"):
        data = json.loads(m.read_text())
        for f in data["files"]:
            assert hashlib.sha256((m.parent / f["name"]).read_bytes()).hexdigest() == f["sha256"]


def test_only_the_damaged_frame_fails_to_decode(samples):
    out, expected = samples
    im = Image.open(out / "dossiers" / expected["corrupt"]["dossier_id"] / "scan_001.tif")
    assert im.n_frames == 3
    ok = []
    for i in range(3):
        im.seek(i)
        try:
            im.load()
            ok.append(True)
        except OSError:
            ok.append(False)
    assert ok == [True, False, True]


def test_golden_questions_cover_the_behaviours(samples):
    out, _ = samples
    golden = [json.loads(line) for line in (out / "golden.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {g["expect"]["behavior"] for g in golden} >= {"answer", "abstain", "partial", "out_of_scope"}
    assert {g["user"] for g in golden} >= {"layla", "sara", "huda"}
