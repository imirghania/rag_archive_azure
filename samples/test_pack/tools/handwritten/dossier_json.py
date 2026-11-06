"""Writes dossier.json (same shape as samples/templates/filled/*/dossier.json) into a folder of scans.
The folder name must be the dossier id. Usage: uv run python samples/test_pack/tools/handwritten/dossier_json.py FOLDER
The web app writes its own manifest; this is only for keeping your scans documented (never upload dossier.json)."""
import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from docai.contracts.keys import DOSSIER_ID_RE  # noqa: E402


def pages(p: Path) -> int:
    if p.suffix.lower() == ".pdf":  # shortcut: counts /Type /Page markers, fine for scanner PDFs, not for page trees in object streams
        return len(re.findall(rb"/Type\s*/Page(?![s\w])", p.read_bytes()))
    with Image.open(p) as im:
        return getattr(im, "n_frames", 1)


def main(folder: str) -> None:
    d = Path(folder).resolve()
    assert DOSSIER_ID_RE.match(d.name), f"folder name {d.name!r} is not a valid dossier id"
    files = sorted(p for p in d.iterdir() if p.suffix.lower() in {".tif", ".tiff", ".pdf", ".png", ".jpg", ".jpeg"})
    assert files, "no scans found"
    man = {"schema": 1, "dossier_id": d.name, "source": "upload", "upload_id": None, "uploaded_by": None, "segmentation": "auto",
           "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "pages": pages(p)} for p in files]}
    (d / "dossier.json").write_text(json.dumps(man, indent=1))
    print(f"wrote {d / 'dossier.json'}: {len(files)} file(s)")


if __name__ == "__main__":
    main(sys.argv[1])
