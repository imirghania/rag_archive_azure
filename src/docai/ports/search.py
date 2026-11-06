"""The search index port."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Protocol

from docai.schemas.rows import SearchHit


class SearchIndex(Protocol):
    def upload(self, index: str, docs: Iterable[dict[str, Any]]) -> None: ...
    def merge(self, index: str, doc: dict[str, Any]) -> bool: ...
    def delete(self, index: str, ids: Iterable[str]) -> None: ...
    def get(self, index: str, doc_id: str) -> dict[str, Any] | None: ...
    def ids(self, index: str, *, document_id: str | None = None, version_lt: int | None = None, injection_suspect: bool | None = None) -> list[str]:
        """IDs of the documents that match every given condition (an OData filter in Azure); no condition lists them all."""
    def put_synonym_map(self, name: str, rules: list[str]) -> None:
        """Replaces the whole map. A new rule takes effect on the next query, without reindexing."""
    def synonym_map(self, name: str) -> list[str]: ...
    def search(self, index: str, *, text: str, vector: list[float],
            acl_groups: list[str], top: int = 8,
            filters: dict[str, Any] | None = None) -> list[SearchHit]:
        """The security filter (`acl_groups` and `injection_suspect ne true`) is applied here, never by the caller."""
