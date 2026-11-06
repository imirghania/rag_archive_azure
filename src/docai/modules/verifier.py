"""app-verifier: four layers decide whether a draft answer may be shown (spec, Workflow 6, Step 9).

Structure, trust tier and numbers are deterministic and carry most of the weight, because the entailment model is of
the same family as the answer agent. A claim is supported only if it passes every layer."""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any

from fastapi import Depends
from pydantic import BaseModel

from docai.contracts import keys
from docai.contracts.enums import TrustTier
from docai.contracts.llm import VerifierOutput
from docai.ports import ClaimResult, Verdict
from docai.resources import prompts
from docai.runtime.context import Context
from docai.runtime.http import make_principal_dep, new_app
from docai.security.access import Principal, access_scope

MARKER = re.compile(r"\[c:([^#\]\s]+)#([^\]\s]+)\]")
_NUMBER = re.compile(r"\d[\d,.٫٬]*\d|\d")
_EASTERN = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")} | {ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")}
_SEP = {ord("٬"): ",", ord("٫"): "."}


def split_claims(draft: str) -> list[str]:
    """Sentences. A piece that starts with a citation marker belongs to the sentence before it, and a very short piece
    ("1." or "Premises.") belongs to the sentence after it, so clause numbers do not split a claim."""
    pieces = [p for p in re.split(r"(?<=[.!?])\s+", draft.strip()) if p.strip()]
    claims: list[str] = []
    carry = ""
    for p in pieces:
        if claims and MARKER.match(p.strip()):
            claims[-1] += " " + p
        elif len(MARKER.sub("", p).split()) <= 2 and not MARKER.search(p):
            carry += p + " "
        else:
            claims.append(carry + p)
            carry = ""
    if carry:
        claims.append(carry.strip())
    return claims


def numbers(text: str) -> set[str]:
    t = MARKER.sub(" ", text).translate(_EASTERN).translate(_SEP)
    return {n.rstrip(".,") for n in _NUMBER.findall(t) if n.rstrip(".,")}


def _norm_numbers(text: str) -> set[str]:
    return numbers(text) | {n.replace(",", "") for n in numbers(text)}


def verify(ctx: Context, *, draft: str, evidence: dict[str, dict[str, Any]], scope: list[str]) -> Verdict:
    results: list[ClaimResult] = []
    blocked: list[str] = []
    to_judge: list[dict[str, Any]] = []
    for i, claim in enumerate(split_claims(draft), start=1):
        cites = [f"{c}#{ln}" for c, ln in MARKER.findall(claim)]
        r = ClaimResult(i, re.sub(r"\s+([.,;:])", r"\1", MARKER.sub("", claim)).strip(), cites, "unsupported")
        results.append(r)
        # 1. structure: a citation exists, every cited chunk was returned to this run, and sits inside the caller's scope
        if not cites:
            r.failed_layer, r.detail = "structure", "no citation"
            continue
        bad = [c for c, ln in MARKER.findall(claim) if c not in evidence or not set(evidence[c].get("acl_groups", [])) & set(scope)
               or ln not in {x["ref"] for x in evidence[c].get("lines", [])}]
        if bad:
            r.failed_layer, r.detail = "structure", f"cited chunk or line not in this run's evidence: {bad[0]}"
            continue
        lines = []
        for c, ln in MARKER.findall(claim):
            doc = evidence[c]
            tier = TrustTier(json.loads(doc.get("trust_tiers_json") or "{}").get(ln, "unverified"))
            text = next(x["text"] for x in doc["lines"] if x["ref"] == ln)
            lines.append({"chunk": c, "ref": ln, "text": text, "tier": tier})
        # 2. trust tier: every cited line must be citable
        rejected = [x for x in lines if not x["tier"].citable]
        if rejected:
            r.failed_layer, r.detail = "trust_tier", f"{rejected[0]['ref']} is {rejected[0]['tier'].value}"
            blocked += [keys.line_key_of_chunk(x["chunk"], x["ref"]) for x in rejected]
            continue
        # 3. numbers: every number in the claim appears in a cited line (after normalising digits and separators)
        have = set().union(*(_norm_numbers(x["text"]) for x in lines))
        missing = [n for n in numbers(r.text) if n not in have and n.replace(",", "") not in have]
        if missing:
            r.failed_layer, r.detail = "numbers", f"{missing[0]} is not in the cited lines"
            continue
        to_judge.append({"claim_id": i, "claim": r.text, "lines": [{"ref": x["ref"], "text": x["text"]} for x in lines]})
    # 4. entailment: a model judges the claims that passed the deterministic layers
    if to_judge:
        out = ctx.chat.complete_json("verifier", prompts.load("verifier"), json.dumps({"claims": to_judge}, ensure_ascii=False), VerifierOutput)
        assert isinstance(out, VerifierOutput)
        by_id = {v.claim_id: v for v in out.verdicts}
        for j in to_judge:
            r = results[j["claim_id"] - 1]
            v = by_id.get(j["claim_id"])
            if v and v.verdict == "supported":
                r.verdict = "supported"
            else:
                r.verdict = v.verdict if v else "unsupported"
                r.failed_layer, r.detail = "entailment", (v.missing if v else "no verdict")
    return Verdict(results, sorted(set(blocked)))


class VerifyRequest(BaseModel):
    draft: str
    evidence: dict[str, dict[str, Any]]


def create_app(ctx: Context):
    app, principal = new_app("app-verifier"), make_principal_dep(ctx)

    @app.post("/verify")
    def run(req: VerifyRequest, p: Principal = Depends(principal)):
        v = verify(ctx, draft=req.draft, evidence=req.evidence, scope=access_scope(ctx.ops.registered_groups(), p.groups))
        return {"claims": [asdict(c) for c in v.claims], "blocked_lines": v.blocked_lines, "ok": v.ok}

    return app


if __name__ == "__main__":
    from docai.runtime.launch import http_app

    http_app(create_app)
