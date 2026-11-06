"""Reading and writing contract-typed artifacts in a BlobStore."""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from docai.ports import AlreadyExists, BlobStore

M = TypeVar("M", bound=BaseModel)


def read_model(blobs: BlobStore, container: str, path: str, model: type[M]) -> M:
    return model.model_validate_json(blobs.read(container, path))


def dump(obj: BaseModel) -> bytes:
    return obj.model_dump_json(by_alias=True, indent=1).encode("utf-8")


def write_model(blobs: BlobStore, container: str, path: str, obj: BaseModel, *, once: bool = False) -> None:
    """once=True is for model outputs: a retry finds the file, reuses it and never calls the model again."""
    blobs.write(container, path, dump(obj), overwrite=not once)


def write_once(blobs: BlobStore, container: str, path: str, data: bytes) -> bool:
    """Returns False when the file already existed (its content stays)."""
    try:
        blobs.write(container, path, data)
        return True
    except AlreadyExists:
        return False
