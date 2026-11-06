"""The blob store port."""
from __future__ import annotations

import builtins
from typing import Protocol


class AlreadyExists(Exception):
    pass


class LeaseLost(Exception):
    """The task's lease token no longer matches: it was reassigned, escalated or already closed."""


class BlobStore(Protocol):
    def read(self, container: str, path: str) -> bytes: ...
    def write(self, container: str, path: str, data: bytes, *, overwrite: bool = False) -> None:
        """overwrite=False is If-None-Match: * and raises AlreadyExists. Deterministic outputs pass overwrite=True."""
    def exists(self, container: str, path: str) -> bool: ...
    def list(self, container: str, prefix: str = "") -> list[str]: ...
    def copy(self, src_container: str, src_path: str, dst_container: str, dst_path: str) -> None: ...
    def write_block(self, container: str, path: str, block_no: int, data: bytes) -> None:
        """Stages one block of a file that arrives in pieces (Azure: stage_block). Re-sending a block replaces it."""
    def list_blocks(self, container: str, path: str) -> builtins.list[int]: ...
    def commit_blocks(self, container: str, path: str, block_count: int) -> int:
        """Joins blocks 0..n-1 into the file and returns its size; the staged blocks are discarded."""
    def scan_result(self, container: str, path: str) -> str:
        """`clean`, `malicious` or `pending` (Azure: the Defender for Storage index tag)."""
    def delete(self, container: str, path: str) -> None: ...
