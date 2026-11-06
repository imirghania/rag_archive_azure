"""Identifier rules (spec, Conventions). Every key carries the revision, so a rescan can never
collide with the first scan. Parsing is strict: a malformed key is a bug, not a value."""
from __future__ import annotations

import re
from dataclasses import dataclass

_DOSSIER = r"(?:[A-Z]{2,3}-C\d{2}-S\d-F\d{4}|UNF-[A-Z]{2,3}-\d{8}-\d{4})"
DOSSIER_ID_RE = re.compile(rf"^{_DOSSIER}$")
DOSSIER_KEY_RE = re.compile(rf"^(?P<dossier>{_DOSSIER})@r(?P<rev>[1-9]\d*)$")
PAGE_KEY_RE = re.compile(rf"^(?P<dossier>{_DOSSIER})@r(?P<rev>[1-9]\d*)/p(?P<page>\d{{3,}})$")
LINE_KEY_RE = re.compile(
    rf"^(?P<dossier>{_DOSSIER})@r(?P<rev>[1-9]\d*)/p(?P<page>\d{{3,}})/L(?P<line>\d+)$"
)
DOCUMENT_ID_RE = re.compile(rf"^(?P<dossier>{_DOSSIER})-r(?P<rev>[1-9]\d*)-D(?P<seq>\d{{2,}})$")
CHUNK_ID_RE = re.compile(
    rf"^(?P<doc>{_DOSSIER}-r[1-9]\d*-D\d{{2,}})__v(?P<ver>[1-9]\d*)__c(?P<n>\d{{4,}})$"
)
# AI Search keys may hold only letters, digits, dash, underscore and equals.
SEARCH_KEY_RE = re.compile(r"^[A-Za-z0-9_\-=]+$")


class KeyError_(ValueError):
    pass


def department_of(dossier_id: str) -> str:
    """FIN-C03-S2-F0117 -> FIN; UNF-FIN-20261104-0007 -> FIN."""
    _check(DOSSIER_ID_RE, dossier_id, "dossier id")
    parts = dossier_id.split("-")
    return parts[1] if parts[0] == "UNF" else parts[0]


def _check(rx: re.Pattern[str], value: str, what: str) -> re.Match[str]:
    m = rx.match(value)
    if not m:
        raise KeyError_(f"not a valid {what}: {value!r}")
    return m


def dossier_key(dossier_id: str, revision: int) -> str:
    _check(DOSSIER_ID_RE, dossier_id, "dossier id")
    if revision < 1:
        raise KeyError_("revision starts at 1")
    return f"{dossier_id}@r{revision}"


def page_key(dossier_id: str, revision: int, page_no: int) -> str:
    return f"{dossier_key(dossier_id, revision)}/p{page_no:03d}"


def line_key(page: str, line_id: str) -> str:
    _check(PAGE_KEY_RE, page, "page key")
    _check(re.compile(r"^L\d+$"), line_id, "line id")
    return f"{page}/{line_id}"


def document_id(dossier_id: str, revision: int, seq: int) -> str:
    _check(DOSSIER_ID_RE, dossier_id, "dossier id")
    return f"{dossier_id}-r{revision}-D{seq:02d}"


def line_key_of_chunk(chunk_id_: str, ref: str) -> str:
    """chunk FIN-C03-S2-F0117-r1-D03__v2__c0002 + ref p014/L17 -> FIN-C03-S2-F0117@r1/p014/L17"""
    doc, _, _ = parse_chunk_id(chunk_id_)
    dossier, rev, _ = parse_document_id(doc)
    return f"{dossier}@r{rev}/{ref}"


def chunk_id(doc_id: str, version: int, n: int) -> str:
    _check(DOCUMENT_ID_RE, doc_id, "document id")
    return f"{doc_id}__v{version}__c{n:04d}"


@dataclass(frozen=True)
class PageRef:
    dossier_id: str
    revision: int
    page_no: int

    @classmethod
    def parse(cls, key: str) -> "PageRef":
        m = _check(PAGE_KEY_RE, key, "page key")
        return cls(m["dossier"], int(m["rev"]), int(m["page"]))

    @property
    def key(self) -> str:
        return page_key(self.dossier_id, self.revision, self.page_no)

    @property
    def department(self) -> str:
        return department_of(self.dossier_id)

    @property
    def dir(self) -> str:
        """Directory of the page inside the `extracted` container."""
        return f"{self.department}/{self.dossier_id}/r{self.revision}/p{self.page_no:03d}/"


@dataclass(frozen=True)
class LineRef:
    page: PageRef
    line_id: str

    @classmethod
    def parse(cls, key: str) -> "LineRef":
        m = _check(LINE_KEY_RE, key, "line key")
        return cls(PageRef(m["dossier"], int(m["rev"]), int(m["page"])), f"L{m['line']}")

    @property
    def key(self) -> str:
        return f"{self.page.key}/{self.line_id}"

    @property
    def short(self) -> str:
        """The form used inside a chunk: p014/L17."""
        return f"p{self.page.page_no:03d}/{self.line_id}"


def parse_dossier_key(key: str) -> tuple[str, int]:
    m = _check(DOSSIER_KEY_RE, key, "dossier key")
    return m["dossier"], int(m["rev"])


def parse_document_id(doc_id: str) -> tuple[str, int, int]:
    m = _check(DOCUMENT_ID_RE, doc_id, "document id")
    return m["dossier"], int(m["rev"]), int(m["seq"])


def parse_chunk_id(cid: str) -> tuple[str, int, int]:
    m = _check(CHUNK_ID_RE, cid, "chunk id")
    return m["doc"], int(m["ver"]), int(m["n"])


# Storage paths

def extracted_dossier_dir(dossier_id: str, revision: int) -> str:
    return f"{department_of(dossier_id)}/{dossier_id}/r{revision}/"


def extracted_document_dir(doc_id: str) -> str:
    d, rev, seq = parse_document_id(doc_id)
    return f"{extracted_dossier_dir(d, rev)}docs/D{seq:02d}/"


def chunks_parquet_path(doc_id: str, version: int) -> str:
    d, _, _ = parse_document_id(doc_id)
    return f"chunks/dept={department_of(d)}/{doc_id}/v{version}.parquet"


def raw_dossier_dir(dossier_id: str, revision: int) -> str:
    """r1 lives directly under the dossier folder; later revisions use an rN subfolder (Workflow 8)."""
    base = f"{department_of(dossier_id)}/{dossier_id}/"
    return base if revision == 1 else f"{base}r{revision}/"
