"""The printable templates: layout facts, zones, the filled example and its trip through the local pipeline."""
import hashlib
import itertools
import json
import shutil

import pytest

pytest.importorskip("PIL")
pdfium = pytest.importorskip("pypdfium2")
from PIL import Image

from docai.app.wiring import build_context
from docai.contracts import keys
from docai.contracts.artifacts import LinesFile, Manifest, OcrResult
from docai.devtools.templates import DOSSIER, MARGIN_X0, generate
from docai.runtime.runner import drain
from docai.core.settings import Settings

from conftest import FIN_EXPERTS, FIN_READERS, FIN_STEWARDS, FIN_TREASURY, HR_READERS, upload

PDFS = ["00_instructions.pdf", "t1_memo_with_margin_note.pdf", "t2_invoice_amounts.pdf",
        "t3_english_and_arabic_notes.pdf", "t4_free_handwriting.pdf", "answer_key_sheet.pdf"]
BLANK = PDFS[1:5]


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root = tmp_path_factory.mktemp("templates")
    out, fix = root / "out", root / "fixtures"
    return out, fix, generate(out, fix)


def render(path, page=0):
    return pdfium.PdfDocument(str(path))[page].render(scale=300 / 72).to_pil().convert("L")


def test_every_file_is_written_and_a4_at_300_dpi(made):
    out = made[0]
    for name in PDFS + ["zones.json", f"filled/{DOSSIER}/scan_001.tif", f"filled/{DOSSIER}/dossier.json"]:
        assert (out / name).is_file(), name
    for name in PDFS:
        pdf = pdfium.PdfDocument(str(out / name))
        w, h = pdf[0].get_size()
        assert (round(w), round(h)) == (595, 842), name
    w, h = render(out / PDFS[1]).size
    assert abs(w - 2480) <= 2 and abs(h - 3508) <= 2
    assert len(pdfium.PdfDocument(str(out / "00_instructions.pdf"))) == 1


def test_zones_are_unique_inside_the_printable_area_and_in_the_answer_key(made):
    out, _, summary = made
    data = json.loads((out / "zones.json").read_text())
    zones = data["zones"]
    ids = [z["id"] for z in zones]
    assert len(ids) == len(set(ids)) == 27
    for z in zones:
        assert 100 <= z["x0"] < z["x1"] <= 2380 and 100 <= z["y0"] < z["y1"] <= 3400, z["id"]
        assert z["template"] in BLANK and z["language"] in ("en", "ar", "en+ar", "digits")
    key_ids = {z.id for z in summary["zones"]}  # the answer key is drawn from exactly these
    assert key_ids == set(ids)
    assert len(pdfium.PdfDocument(str(out / "answer_key_sheet.pdf"))) == 2


def test_the_memo_margin_zone_is_wide_and_wholly_right_of_the_printed_text(made):
    summary = made[2]
    edge = summary["printed_right_edge"]["t1_memo_with_margin_note.pdf"]
    margin = [z for z in summary["zones"] if z.template.startswith("t1") and z.x0 == MARGIN_X0]
    assert len(margin) == 3
    for z in margin:
        assert z.x0 - edge >= 100, "printed text must end well left of the margin zone"
        assert z.x1 - z.x0 >= 710  # 6 cm
    ys = [z.ruled_lines[0] for z in margin]
    assert [b - a for a, b in itertools.pairwise(ys)] == [110, 110]
    long_lines = max(z.x1 - z.x0 for z in summary["zones"] if z.template.startswith("t4"))
    assert long_lines >= 710


def test_blank_templates_have_ruling_but_blank_zones(made):
    out, _, summary = made
    pages = {name: render(out / name) for name in BLANK}

    def count_below(img, box, level):
        return sum(img.crop(box).histogram()[:level])

    for z in summary["zones"]:
        img = pages[z.template]
        assert count_below(img, (z.x0 + 8, z.y0 + 8, z.x1 - 8, z.y1 - 8), 100) < 20, f"{z.id} is not blank"
        assert count_below(img, (z.x0, z.y0, z.x1 + 1, z.y1 + 1), 200) > 200, f"{z.id} has no ruling or box"


def test_pages_start_new_documents(made):
    _, _, summary = made
    refs = set()
    for t in summary["templates"]:
        titles = [ln.text for ln in t.lines if ln.bold and ln.text.isupper() and len(ln.text.split()) >= 2]
        assert len(titles) == 1
        refs |= {ln.text for ln in t.lines if ln.text.startswith("Ref: FIN/TPL/")}
    assert len(refs) == 4


def test_manifest_matches_the_filled_dossier(made):
    out, _, _ = made
    d = out / "filled" / DOSSIER
    m = Manifest.model_validate_json((d / "dossier.json").read_text())
    assert m.dossier_id == DOSSIER and keys.DOSSIER_ID_RE.match(m.dossier_id)
    for f in m.files:
        data = (d / f.name).read_bytes()
        assert (f.bytes, f.sha256) == (len(data), hashlib.sha256(data).hexdigest())
    im = Image.open(d / "scan_001.tif")
    assert (im.n_frames, im.size, m.files[0].pages) == (3, (2480, 3508), 3)


def test_fixtures_validate(made):
    _, fix, _ = made
    files = sorted((fix / DOSSIER).glob("*.ocr.json"))
    assert len(files) == 3
    for f in files:
        ocr = OcrResult.model_validate_json(f.read_text())
        assert any(ln.style == "handwritten" for ln in ocr.lines)
        vlm = json.loads(f.with_name(f.name.replace(".ocr.", ".vlm.")).read_text())
        assert {ln.id for ln in ocr.lines if ln.style == "handwritten"} == set(vlm)


def test_generation_is_deterministic(made, tmp_path):
    out, _, _ = made
    generate(tmp_path / "again")
    for name in (f"filled/{DOSSIER}/scan_001.tif", f"filled/{DOSSIER}/dossier.json", "zones.json"):
        assert (out / name).read_bytes() == (tmp_path / "again" / name).read_bytes(), name


def test_the_filled_dossier_runs_locally_and_raises_review_tasks(made, tmp_path, pg_url):
    out, fix, _ = made
    base = tmp_path / "base"
    shutil.copytree(out / "filled" / DOSSIER, base / "dossiers" / DOSSIER)
    shutil.copytree(fix, base / "fixtures")
    settings = Settings(_env_file=None, adapters="local", local_fixtures_dir=base / "fixtures", local_dir=tmp_path / "local",
                        database={"url": pg_url})
    ctx = build_context(settings, root=tmp_path / "local")
    ctx.ops.reset_for_tests()
    ctx.samples = base  # type: ignore[attr-defined]
    for code, name in (("FIN", "Finance"), ("HR", "Human Resources")):
        ctx.ops.add_department(code, name)
    for gid, dept, kind, name in [(FIN_READERS, "FIN", "reader", "fin-readers"), (FIN_EXPERTS, "FIN", "expert", "fin-experts"),
                                  (FIN_STEWARDS, "FIN", "steward", "fin-stewards"), (FIN_TREASURY, "FIN", "restricted", "fin-treasury"),
                                  (HR_READERS, "HR", "reader", "hr-readers")]:
        ctx.ops.add_access_group(gid, dept, kind, name)
    upload(ctx, DOSSIER)
    drain(ctx)
    d = ctx.ops.get_dossier(DOSSIER, 1)
    assert (d.status, d.total_pages, d.pages_failed) == ("completed", 3, 0)
    assert len(ctx.ops.list_documents(DOSSIER, 1)) == 3  # one document per template page

    def lines(page):
        raw = ctx.blobs.read("extracted", keys.PageRef(DOSSIER, 1, page).dir + "lines.v1.json")
        return LinesFile.model_validate_json(raw).lines

    memo = lines(1)
    notes = [ln for ln in memo if ln.placement == "right_margin"]
    assert notes[0].text == "Approved, pay 1,750 by 15/3" and len({ln.anchor for ln in notes}) == 1
    assert all(ln.placement == "main" for p in (2, 3) for ln in lines(p))  # nothing else is mistaken for a margin note
    tiers = [ln.tier.value for p in (1, 2, 3) for ln in lines(p)]
    assert tiers.count("unverified") == 3 and "handwritten_dual_agreed" in tiers
    tasks = ctx.ops.list_tasks("FIN", "open")
    assert len(tasks) == 3 and {t["reason"] for t in tasks} == {"readers_disagree", "ocr_too_unsure"}
