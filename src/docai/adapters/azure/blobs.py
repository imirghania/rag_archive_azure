"""ADLS Gen2 adapter of the BlobStore port, through the Blob API (Entra authentication, no keys). `raw` is write-once: every
write there uses If-None-Match, and the container's retention policy is the second line of defence."""
from __future__ import annotations

import base64
import builtins
from typing import Any

from docai.core.catalog import CONTAINERS
from docai.core.settings import Settings
from docai.ports import AlreadyExists

_SCAN_TAG = "Malware Scanning scan result"


def _block_id(n: int) -> str:
    return base64.b64encode(f"{n:06d}".encode()).decode()


class AdlsBlobStore:
    def __init__(self, settings: Settings, 
                credential: Any = None, *, 
                services: dict[str, Any] | None = None) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        self.cred = credential or DefaultAzureCredential()
        a = settings.azure
        self.accounts = {
            "raw": a.storage_raw_account, 
            "proc": a.storage_proc_account, 
            "staging": a.storage_staging_account
            }
        self.services = (services or 
                        {k: BlobServiceClient(f"https://{v}.blob.core.windows.net", self.cred) 
                            for k, v in self.accounts.items() if v})

    def _blob(self, container: str, path: str):
        return self.services[CONTAINERS[container]].get_blob_client(container, path)

    def read(self, container: str, path: str) -> bytes:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return self._blob(container, path).download_blob().readall()
        except ResourceNotFoundError as e:
            raise FileNotFoundError(f"{container}/{path}") from e

    def write(self, container: str, path: str, data: bytes, *, overwrite: bool = False) -> None:
        from azure.core.exceptions import ResourceExistsError

        try:
            self._blob(container, path).upload_blob(data, overwrite=overwrite)  # overwrite=False sends If-None-Match: *
        except ResourceExistsError as e:
            raise AlreadyExists(f"{container}/{path}") from e

    def exists(self, container: str, path: str) -> bool:
        return self._blob(container, path).exists()

    def list(self, container: str, prefix: str = "") -> list[str]:
        cc = self.services[CONTAINERS[container]].get_container_client(container)
        return sorted(b.name for b in cc.list_blobs(name_starts_with=prefix or None) if not b.name.endswith(".blocks") and ".blocks/" not in b.name)

    def copy(self, src_container: str, src_path: str, dst_container: str, dst_path: str) -> None:
        """A synchronous server-side copy; between two accounts the source is authorised with the caller's own token."""
        src = self._blob(src_container, src_path)
        token = self.cred.get_token("https://storage.azure.com/.default").token
        self._blob(dst_container, dst_path).start_copy_from_url(src.url, requires_sync=True, source_authorization=f"Bearer {token}")

    def delete(self, container: str, path: str) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            self._blob(container, path).delete_blob()
        except ResourceNotFoundError:
            pass

    # files that arrive in blocks
    def write_block(self, container: str, path: str, block_no: int, data: bytes) -> None:
        self._blob(container, path).stage_block(_block_id(block_no), data)  # uncommitted blocks wait up to a week

    def list_blocks(self, container: str, path: str) -> builtins.list[int]:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            _, uncommitted = self._blob(container, path).get_block_list("uncommitted")
        except ResourceNotFoundError:
            return []
        return sorted(int(base64.b64decode(b.id).decode()) for b in uncommitted)

    def commit_blocks(self, container: str, path: str, block_count: int) -> int:
        from azure.storage.blob import BlobBlock

        have = self.list_blocks(container, path)
        if have != list(range(block_count)):
            raise ValueError(f"blocks {sorted(set(range(block_count)) - set(have))} are missing")
        blob = self._blob(container, path)
        blob.commit_block_list([BlobBlock(block_id=_block_id(n)) for n in range(block_count)])
        return blob.get_blob_properties().size

    def scan_result(self, container: str, path: str) -> str:
        """Defender for Storage writes the result to the blob's index tags; no tag yet means the scan is pending."""
        tags = self._blob(container, path).get_blob_tags()
        v = tags.get(_SCAN_TAG, "")
        return "pending" if not v else ("clean" if v == "No threats found" else "malicious")
