"""Deterministic MessageIds (spec, Conventions). A deliberate re-send must change the ID, or Service
Bus drops the new message as a duplicate of the old one."""
from __future__ import annotations


def message_id(step: str, subject: str, *, version: int | None = None) -> str:
    base = f"{step}:{subject}"
    return f"{base}:v{version}" if version is not None else base


def resend(mid: str, n: int) -> str:
    if n < 1:
        raise ValueError("resend numbers start at 1")
    return f"{mid}:resend{n}"


def retry_try(mid: str, n: int) -> str:
    """Used by the upload commit while a scan result is pending; the first send has no suffix."""
    if n < 2:
        raise ValueError("the first send has no suffix; tries start at 2")
    return f"{mid}:try{n}"


def redrive(mid: str, n: int = 1) -> str:
    return f"{mid}:redrive{n}"


def intake(dossier_id: str, manifest_hash: str) -> str:
    return f"intake:{dossier_id}:{manifest_hash}"


def reprocess(dossier_id: str, next_revision: int) -> str:
    return f"reprocess:{dossier_id}:r{next_revision}"
