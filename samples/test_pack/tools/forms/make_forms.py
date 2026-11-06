"""Builds the blank forms (PDF + PNG), zones.json, previews and the documents.

    uv run python samples/test_pack/tools/forms/make_forms.py

Deterministic: same pixels every run (PDF bytes differ only by timestamps). Writes to samples/test_pack/forms/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib import preview  # noqa: E402
from forms import FORMS  # noqa: E402
from docai.contracts.keys import DOSSIER_ID_RE  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "forms"


def main() -> None:
    (OUT / "preview_filled").mkdir(parents=True, exist_ok=True)
    forms = [make() for make in FORMS]
    zones, warns = [], []
    for f in forms:
        assert DOSSIER_ID_RE.match(f.dossier), f.dossier
        f.img.save(OUT / f"{f.code}_{f.slug}.png", dpi=(300, 300), optimize=True)
        f.img.save(OUT / f.file, "PDF", resolution=300.0, quality=92)
        img, w = preview(f)
        warns += w
        img.save(OUT / "preview_filled" / f"PREVIEW_{f.code}_{f.slug}.png", dpi=(300, 300), optimize=True)
        zones += [{"id": z.id, "template": f.file, "form": f.code, "page": 1, "x0": z.x0, "y0": z.y0, "x1": z.x1, "y1": z.y1,
                   "language": z.language, "purpose": z.purpose, "ruled_lines": z.ruled_lines, "kind": z.kind} for z in f.zones]
        print(f.code, f.lang, len(f.zones), "zones")
    (OUT / "zones.json").write_text(json.dumps({"page": {"width": 2480, "height": 3508, "dpi": 300}, "zones": zones}, indent=1) + "\n")
    print("\n".join(warns) or "no overflow warnings")
    try:
        from docs import write_docs
    except ImportError:
        return
    write_docs(forms, OUT)


if __name__ == "__main__":
    main()
