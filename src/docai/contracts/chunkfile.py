"""The chunk Parquet file written by job-chunk-embed and read by job-index (and later by a rebuild job)."""
from __future__ import annotations

import io
import json

import pyarrow as pa
import pyarrow.parquet as pq

from .artifacts import ChunkRecord


def to_parquet(chunks: list[ChunkRecord]) -> bytes:
    rows = []
    for c in chunks:
        d = c.model_dump(mode="json", by_alias=True)
        d["trust_tiers_json"] = json.dumps(d.pop("trust_tiers"), ensure_ascii=False)
        rows.append(d)
    buf = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows), buf, compression="zstd")
    return buf.getvalue()


def from_parquet(data: bytes) -> list[ChunkRecord]:
    out = []
    for row in pq.read_table(io.BytesIO(data)).to_pylist():
        row["trust_tiers"] = json.loads(row.pop("trust_tiers_json"))
        out.append(ChunkRecord.model_validate(row))
    return out
