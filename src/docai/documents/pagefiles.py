"""Reading the newest page files of a document (shared by the metadata and chunking jobs)."""
from __future__ import annotations

import re

from docai.contracts import keys
from docai.contracts.artifacts import LinesFile
from docai.ports import BlobStore

from .artifactio import read_model


def document_lines(blobs: BlobStore, dossier_id: str, rev: int, first: int, last: int, upto_version: int | None = None) -> list[tuple[int, LinesFile]]:
    """The newest lines.vN.json of each page (not newer than `upto_version` when given)."""
    out = []
    for n in range(first, last + 1):
        pdir = keys.PageRef(dossier_id, rev, n).dir
        vs = sorted(int(m[1]) for p in blobs.list("extracted", pdir) if (m := re.search(r"lines\.v(\d+)\.json$", p)))
        v = max(x for x in vs if upto_version is None or x <= upto_version)
        out.append((n, read_model(blobs, "extracted", f"{pdir}lines.v{v}.json", LinesFile)))
    return out
