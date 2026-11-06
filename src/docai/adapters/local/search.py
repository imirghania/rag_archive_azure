"""In-memory search index: a keyword score plus cosine similarity, with the same security filter as the real index."""
from __future__ import annotations

import math
import re
from collections.abc import Iterable
from typing import Any

from docai.ports import SearchHit

_TOKEN = re.compile(r"[a-z0-9؀-ۿ]+")
_TEXT_FIELDS = ("text_en", "text_ar", "subject", "reference", "doc_type")


def _tokens(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


class MemorySearch:
    def __init__(self) -> None:
        self.indexes: dict[str, dict[str, dict[str, Any]]] = {}
        self.synonyms: dict[str, list[str]] = {}

    def put_synonym_map(self, name: str, rules: list[str]) -> None:
        self.synonyms[name] = list(rules)

    def synonym_map(self, name: str) -> list[str]:
        return self.synonyms.get(name, [])

    def _ix(self, index: str) -> dict[str, dict[str, Any]]:
        return self.indexes.setdefault(index, {})

    def upload(self, index: str, docs: Iterable[dict[str, Any]]) -> None:
        key = "hint_id" if index == "notes" else "chunk_id"
        for d in docs:
            self._ix(index)[d[key]] = dict(d)

    def merge(self, index: str, doc: dict[str, Any]) -> bool:
        key = "hint_id" if index == "notes" else "chunk_id"
        cur = self._ix(index).get(doc[key])
        if cur is None:
            return False  # a merge into a chunk the index does not hold yet creates nothing
        cur.update(doc)
        return True

    def delete(self, index: str, ids: Iterable[str]) -> None:
        for i in ids:
            self._ix(index).pop(i, None)

    def get(self, index: str, doc_id: str) -> dict[str, Any] | None:
        return self._ix(index).get(doc_id)

    def ids(self, index: str, *, document_id=None, 
            version_lt=None, injection_suspect=None) -> list[str]:
        def ok(d):
            return ((document_id is None or d.get("document_id") == document_id) and 
                    (version_lt is None or d.get("version", 0) < version_lt) and 
                    (injection_suspect is None or bool(d.get("injection_suspect")) == injection_suspect))
        return sorted(i for i, d in self._ix(index).items() if ok(d))

    def search(self, index: str, *, text: str, 
            vector: list[float], acl_groups: list[str], top: int = 8,
            filters: dict[str, Any] | None = None) -> list[SearchHit]:
        scope = set(acl_groups)
        q = set(_tokens(text))
        for rule in (r for rules in self.synonyms.values() for r in rules):
            terms = [set(_tokens(x)) for x in rule.split(",")]
            if any(t and t <= q for t in terms):
                q |= set().union(*terms)
        hits = []
        for doc_id, d in self._ix(index).items():
            if not scope & set(d.get("acl_groups", [])) or d.get("injection_suspect"):
                continue  # the security filter: never optional
            if any(d.get(k) != v for k, v in (filters or {}).items()):
                continue
            body = _tokens(" ".join(str(d.get(f, "")) for f in _TEXT_FIELDS))
            kw = sum(1 for t in body if t in q) / math.sqrt(len(body) or 1)
            vec = d.get("text_vector") or []
            cos = sum(a * b for a, b in zip(vector, vec)) if vec and vector else 0.0
            score = kw + 2.0 * cos
            if score > 0:
                hits.append(SearchHit(doc_id, score, d))
        return sorted(hits, key=lambda h: -h.score)[:top]
