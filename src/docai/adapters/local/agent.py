"""A scripted stand-in for the Foundry answer agent, so the answering path and the golden questions run offline.

It does what a careless agent would: searches, then cites the best-matching line it can see, whatever its trust tier.
That is deliberate, so the verifier is the layer that is tested (an unverified line must never reach the user)."""
from __future__ import annotations

import json
import math
import re
from typing import Any

from docai.ports import ToolCall, ToolExecutor

_TOKEN = re.compile(r"[a-z0-9؀-ۿ]+")
_ASKS_NUMBER = re.compile(r"\b(how much|amount|cost|total|price|spend|spent|paid)\b|كم", re.I)


class ScriptedAgent:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.corrections: list[str] = []

    def run(self, *, question: str, queries: dict[str, str], history: list[dict[str, Any]], tools: ToolExecutor, correction: str | None = None) -> str:
        if correction:
            self.corrections.append(correction)
        query = queries.get("en") or queries.get("ar") or question
        self.calls.append(query)
        hits = json.loads(tools(ToolCall("search_documents", {"query": query, "language": "en", "top": 8})))
        notes = json.loads(tools(ToolCall("search_notes", {"query": query, "top": 3})))
        if notes:  # an expert note explains an internal name: search again with the documents' own words
            more = json.loads(tools(ToolCall("search_documents", {"query": notes[0]["text"], "language": "en", "top": 8})))
            seen = {h["chunk_id"] for h in hits}
            hits += [h for h in more if h["chunk_id"] not in seen]
        q = set(_TOKEN.findall(query.lower())) - {"the", "for", "was", "and", "how", "much"}
        wants_number = bool(_ASKS_NUMBER.search(question))
        # rare words weigh more (inverse document frequency over the lines it was shown), as a reader would weigh them
        all_lines = [(h, ln) for h in hits for ln in h["lines"]]
        df: dict[str, int] = {}
        for _, ln in all_lines:
            for w in set(_TOKEN.findall(ln["text"].lower())):
                df[w] = df.get(w, 0) + 1
        best, best_score = None, 0.0
        for h, ln in all_lines:
            words = set(_TOKEN.findall(ln["text"].lower()))
            score = sum(math.log(1 + len(all_lines) / df[w]) for w in q & words)
            if wants_number:
                # an answer to "how much was <verb>ed" contains a number the question did not, and a word of that verb
                has_new_number = bool(set(re.findall(r"\d[\d,.]*\d|\d", ln["text"])) - q)
                verbs = {w[:5] for w in q if w.endswith("ed") or w.endswith("ing")}
                if not has_new_number or (verbs and not verbs & {w[:5] for w in words}):
                    score = 0
            if score > best_score:
                best, best_score = (h, ln), score
        if not best:
            note = f" (an expert note mentions it: {notes[0]['text'][:80]})" if notes else ""
            return f"NO_EVIDENCE: searched for '{query}' and found nothing that answers it{note}"
        h, ln = best
        text = ln["text"].strip().rstrip(".")
        marker = f"[c:{h['chunk_id']}#{ln['ref']}]"
        # a line can hold several sentences; each sentence of the draft carries its own citation, as the agent prompt asks
        return " ".join(f"{s.rstrip('.')} {marker}." for s in re.split(r"(?<=[.!?])\s+", text) if s.strip())
