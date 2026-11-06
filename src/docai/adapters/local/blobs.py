"""A folder on disk as the blob store. Containers are sub-folders; write-once is an exclusive create."""
from __future__ import annotations

import builtins
import os
import shutil
from pathlib import Path

from docai.ports import AlreadyExists


class LocalBlobStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, container: str, path: str) -> Path:
        p = (self.root / container / path).resolve()
        if not str(p).startswith(str((self.root / container).resolve())):
            raise ValueError(f"path escapes the container: {path}")
        return p

    def read(self, container: str, path: str) -> bytes:
        return self._p(container, path).read_bytes()

    def write(self, container: str, path: str, data: bytes, *, overwrite: bool = False) -> None:
        p = self._p(container, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if overwrite:
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, p)
            return
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as e:
            raise AlreadyExists(f"{container}/{path}") from e
        with os.fdopen(fd, "wb") as f:
            f.write(data)

    def exists(self, container: str, path: str) -> bool:
        return self._p(container, path).is_file()

    def list(self, container: str, prefix: str = "") -> list[str]:
        base = self.root / container
        if not base.exists():
            return []
        return sorted(str(p.relative_to(base)) 
                    for p in base.rglob("*")
                    if (p.is_file() and not p.name.endswith(".tmp") and 
                        not p.name.startswith(".") and 
                        ".blocks/" not in str(p.relative_to(base)) and 
                        str(p.relative_to(base)).startswith(prefix))
                    )

    def copy(self, src_container: str, src_path: str, dst_container: str, dst_path: str) -> None:
        dst = self._p(dst_container, dst_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._p(src_container, src_path), dst)

    def delete(self, container: str, path: str) -> None:
        self._p(container, path).unlink(missing_ok=True)

    # files that arrive in blocks, and the malware scan result
    def _blocks_dir(self, container: str, path: str) -> Path:
        return self._p(container, path + ".blocks")

    def write_block(self, container: str, path: str, block_no: int, data: bytes) -> None:
        d = self._blocks_dir(container, path)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{block_no:06d}").write_bytes(data)

    def list_blocks(self, container: str, path: str) -> builtins.list[int]:
        d = self._blocks_dir(container, path)
        return sorted(int(p.name) for p in d.iterdir()) if d.exists() else []

    def commit_blocks(self, container: str, path: str, block_count: int) -> int:
        d = self._blocks_dir(container, path)
        have = self.list_blocks(container, path)
        if have != list(range(block_count)):
            raise ValueError(f"blocks {sorted(set(range(block_count)) - set(have))} are missing")
        dst = self._p(container, path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with open(dst, "wb") as out:
            for n in have:
                chunk = (d / f"{n:06d}").read_bytes()
                out.write(chunk)
                size += len(chunk)
        shutil.rmtree(d)
        return size

    EICAR = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"

    def scan_result(self, container: str, path: str) -> str:
        """A stand-in for the Defender tag: files whose name starts with `pending` stay pending, EICAR content is malicious."""
        if ( Path(path).name.startswith("pending") and 
            not (self._p(container, path).parent / ".scanned").exists() ):
            return "pending"
        return "malicious" if self.EICAR in self._p(container, path).read_bytes() else "clean"

    def finish_scan(self, container: str, path: str) -> None:  # test hook: the pending scan completes
        (self._p(container, path).parent / ".scanned").write_text("1")
