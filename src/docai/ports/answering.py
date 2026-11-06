"""Answering-service ports: the agent, retrieval and the verifier."""
from __future__ import annotations

from typing import Any, Protocol

from docai.schemas.rows import ToolCall, Verdict


class ToolExecutor(Protocol):
    def __call__(self, call: ToolCall) -> str:
        """Runs one tool the agent asked for, with the caller's access scope, and returns the output as JSON text."""


class AnswerAgent(Protocol):
    """The Foundry agent `docai-answer-agent`. It can only ask for tools; the caller executes them (spec, Workflow 6)."""

    def run(self, *, question: str, queries: dict[str, str], history: list[dict[str, Any]], tools: ToolExecutor,
            correction: str | None = None) -> str:
        """Returns the draft: prose with citation markers `[c:<chunk_id>#<page>/<line>]`, or `NO_EVIDENCE: ...`."""


class Retrieval(Protocol):
    """app-retrieval. The security filter is applied here, from the scope the caller passes."""

    def search_documents(self, *, scope: list[str], query: str, language: str, top: int, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...
    def search_notes(self, *, scope: list[str], query: str, top: int) -> list[dict[str, Any]]: ...


class Verifier(Protocol):
    """app-verifier: structure, trust tier and numbers are deterministic; entailment is judged by a model."""

    def verify(self, *, draft: str, evidence: dict[str, dict[str, Any]], scope: list[str]) -> Verdict: ...
