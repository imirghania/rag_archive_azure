"""DocumentConverter adapter: LibreOffice, installed in the job image (deploy/Dockerfile)."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class LibreOfficeConverter:
    def __init__(self, binary: str | None = None, timeout: int = 180) -> None:
        self.binary = binary or shutil.which("soffice") or shutil.which("libreoffice") or "soffice"
        self.timeout = timeout

    def to_pdf(self, data: bytes, filename: str) -> bytes:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ("doc", "docx", "txt"):
            raise ValueError(f"cannot convert .{ext}")
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / f"input.{ext}"
            src.write_bytes(data)
            # a private profile directory: concurrent conversions must not share LibreOffice's lock files
            subprocess.run([self.binary, "--headless", "--norestore", 
                            f"-env:UserInstallation=file://{d}/profile", 
                            "--convert-to", "pdf", "--outdir", d, str(src)],
                        check=True, timeout=self.timeout, capture_output=True)
            out = Path(d) / "input.pdf"
            if not out.exists():
                raise RuntimeError("LibreOffice produced no PDF")
            return out.read_bytes()
