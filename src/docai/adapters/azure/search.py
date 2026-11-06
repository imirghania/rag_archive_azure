"""AI Search adapter. Callers use the logical names `docs` and `notes`, which are the indexes `docs-v1` and `notes-v1` (no aliases: D48); the security filter is built here from the scope, so no caller
can forget it. Vectors are computed by the caller (the Embedder port), which keeps vectorizer settings out of the index."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from docai.ports import SearchHit
from docai.resources import searchdefs

KEYS = {"docs": "chunk_id", "notes": "hint_id"}
SEMANTIC = {"docs": "docs-semantic", "notes": "notes-semantic"}
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def q(value: str) -> str:
    """An OData string literal: single quotes are doubled."""
    return "'" + str(value).replace("'", "''") + "'"


def security_filter(acl_groups: list[str], 
                    extra: dict[str, Any] | None = None, *, 
                    with_injection: bool = True) -> str:
    if not acl_groups:
        return "acl_groups/any(g: g eq '__none__')"  # an empty scope matches nothing
    parts = [f"acl_groups/any(g: search.in(g, {q(','.join(acl_groups))}, ','))"]
    if with_injection:
        parts.append("injection_suspect ne true")
    for k, v in (extra or {}).items():
        if not re.fullmatch(r"[a-z_]+", k):
            raise ValueError(f"bad filter field {k!r}")
        parts.append(f"{k} eq {q(v)}")
    return " and ".join(parts)


def prepare(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    if isinstance(out.get("doc_date"), str) and _DATE_ONLY.match(out["doc_date"]):
        out["doc_date"] = out["doc_date"] + "T00:00:00Z"  # the index field is a DateTimeOffset
    return out


class AzureSearch:
    def __init__(self, endpoint: str, 
                credential: Any = None, *, 
                clients: dict[str, Any] | None = None, 
                index_client: Any = None) -> None:
        from azure.identity import DefaultAzureCredential

        self.endpoint = endpoint
        self.cred = credential or DefaultAzureCredential()
        self._clients: dict[str, Any] = clients or {}
        self._index_client = index_client

    def _c(self, index: str):
        if index not in self._clients:
            from azure.search.documents import SearchClient
            self._clients[index] = SearchClient(self.endpoint, searchdefs.index_name(index), self.cred)
        return self._clients[index]

    def _ic(self):
        if self._index_client is None:
            from azure.search.documents.indexes import SearchIndexClient
            self._index_client = SearchIndexClient(self.endpoint, self.cred)
        return self._index_client

    def upload(self, index: str, docs: Iterable[dict[str, Any]]) -> None:
        batch = [prepare(d) for d in docs]
        for i in range(0, len(batch), 500):  # mergeOrUpload: a chunk ID carries its version, so v1 never overwrites v2
            res = self._c(index).merge_or_upload_documents(batch[i:i + 500])
            failed = [r for r in res if not r.succeeded]
            if failed:
                raise RuntimeError(f"{len(failed)} document(s) were not indexed: {failed[0].key} {failed[0].error_message}")

    def merge(self, index: str, doc: dict[str, Any]) -> bool:
        """False when the document is not there yet: a merge must never create an incomplete document."""
        res = self._c(index).merge_documents([prepare(doc)])
        return bool(res[0].succeeded)

    def delete(self, index: str, ids: Iterable[str]) -> None:
        ids = list(ids)
        if ids:
            self._c(index).delete_documents([{KEYS[index]: i} for i in ids])

    def get(self, index: str, doc_id: str) -> dict[str, Any] | None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return dict(self._c(index).get_document(key=doc_id))
        except ResourceNotFoundError:
            return None

    def ids(self, index: str, *, 
            document_id: str | None = None, 
            version_lt: int | None = None, 
            injection_suspect: bool | None = None) -> list[str]:
        conds = []
        if document_id is not None:
            conds.append(f"document_id eq {q(document_id)}")
        if version_lt is not None:
            conds.append(f"version lt {int(version_lt)}")
        if injection_suspect is not None:
            conds.append(f"injection_suspect eq {str(injection_suspect).lower()}")
        res = self._c(index).search(
            search_text="*", 
            filter=" and ".join(conds) or None, select=[KEYS[index]], 
            top=100000
            )
        return sorted(r[KEYS[index]] for r in res)

    def search(self, index: str, *, text: str, 
            vector: list[float], acl_groups: list[str], 
            top: int = 8, filters: dict[str, Any] | None = None
            ) -> list[SearchHit]:
        from azure.search.documents.models import VectorizedQuery

        kw: dict[str, Any] = {}
        if vector:
            kw["vector_queries"] = [
                VectorizedQuery(vector=vector, k_nearest_neighbors=50, fields="text_vector")
                ]
        res = self._c(index).search(
            search_text=text, 
            filter=security_filter(acl_groups, filters, with_injection=index == "docs"), 
            top=top, query_type="semantic", 
            semantic_configuration_name=SEMANTIC[index], **kw
            )
        hits = []
        for r in res:
            d = {k: v for k, v in r.items() if not k.startswith("@")}
            hits.append(
                SearchHit(d[KEYS[index]], 
                        float(r.get("@search.reranker_score") or 
                            r.get("@search.score") or 
                            0.0), 
                        d)
                )
        return hits

    def put_synonym_map(self, name: str, rules: list[str]) -> None:
        from azure.search.documents.indexes.models import SynonymMap
        self._ic().create_or_update_synonym_map(SynonymMap(name=name, synonyms=rules))

    def synonym_map(self, name: str) -> list[str]:
        m = self._ic().get_synonym_map(name)
        return (list(m.synonyms) 
                if not isinstance(m.synonyms, str) 
                else [x for x in m.synonyms.split("\n") if x]
                )
