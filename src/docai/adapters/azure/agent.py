"""AnswerAgent adapter: the Foundry agent `docai-answer-agent` (Responses-based agents, azure-ai-projects 2.x).

The agent can only ask for tools; this code executes them with the caller's scope (spec: the model never sees or sets
permissions). Every question runs on its own chain of responses, which are deleted when the answer is done, so retrieved chunks
do not stay in a thread after an access change or a leaver (spec, Open items: Foundry threads).

UNVERIFIED AGAINST THE LIVE SERVICE: written from the azure-ai-projects 2.0 documentation and tested against a stub that has the
documented shape. The first real run is the test; everything Foundry-specific is in this one file."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from docai.core.settings import Settings
from docai.ports import ToolCall, ToolExecutor
from docai.resources import prompts

log = logging.getLogger("docai.agent")
AGENT_NAME = "docai-answer-agent"
MAX_TOOL_ROUNDS = 6

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_documents", 
        "description": "Search the archive's documents. Returns chunks with their lines and citation IDs.",
        "parameters": {
            "type": "object", 
            "properties": {
                "query": {"type": "string"}, 
                "language": {"type": "string", "enum": ["en", "ar"]}, 
                "top": {"type": "integer"}
                },
            "required": ["query", "language", "top"], 
            "additionalProperties": False
            }
        },
    {
        "name": "search_notes", 
        "description": "Search approved expert notes that explain internal names and terms.",
        "parameters": {
            "type": "object", 
            "properties": {"query": {"type": "string"}, "top": {"type": "integer"}}, 
            "required": ["query", "top"], 
            "additionalProperties": False
            }
    },
]


def definition_hash(settings: Settings) -> str:
    return hashlib.sha256(json.dumps(
        [settings.models.answer_agent, prompts.load("agent"), TOOLS], 
        sort_keys=True
        ).encode() ).hexdigest()[:16]


def ensure_agent(project: Any, settings: Settings) -> str:
    """Creates a new agent version only when the model, the instructions or the tools changed. Run by the bootstrap script."""
    from azure.ai.projects.models import FunctionTool, PromptAgentDefinition

    h = definition_hash(settings)
    try:
        latest = project.agents.get(agent_name=AGENT_NAME)
        if ((getattr(getattr(latest, "versions", None), "latest", None) or latest).metadata or {}).get("definition_hash") == h:
            return h
    except Exception:  # noqa: BLE001 - not found (first run), or an SDK shape this code does not know: create a version
        log.info("creating the agent version")
    project.agents.create_version(agent_name=AGENT_NAME, 
                                metadata={"definition_hash": h}, 
                                definition=PromptAgentDefinition(
                                    model=settings.models.answer_agent, 
                                    instructions=prompts.load("agent"), 
                                    tools=[FunctionTool(strict=True, **t) for t in TOOLS]
                                    )
                                )
    return h


class FoundryAnswerAgent:
    def __init__(self, settings: Settings, *, openai_client: Any = None, project: Any = None) -> None:
        self.s = settings
        if openai_client is None:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential
            project = project or AIProjectClient(endpoint=settings.azure.foundry_project_endpoint, credential=DefaultAzureCredential())
            openai_client = project.get_openai_client()
        self.client = openai_client
        self.ref = {"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}}

    def run(self, *, question: str, 
            queries: dict[str, str], 
            history: list[dict[str, Any]], 
            tools: ToolExecutor, correction: str | None = None) -> str:
        hist = [m for h in history for m in (
            {"type": "message", "role": "user", "content": h["question"]}, 
            {"type": "message", "role": "assistant", "content": h["answer"] or ""}
            )]
        prompt = f"{question}\n\nSearch hints: English query: {queries.get('en') or '-'}; Arabic query: {queries.get('ar') or '-'}."
        if correction:
            prompt += f"\n\nCorrection needed: {correction}"
        ids: list[str] = []
        try:
            resp = self.client.responses.create(input=[*hist, {"type": "message", "role": "user", "content": prompt}], extra_body=self.ref)
            ids.append(resp.id)
            for _ in range(MAX_TOOL_ROUNDS):
                calls = [it for it in resp.output if getattr(it, "type", "") == "function_call"]
                if not calls:
                    return (resp.output_text or "").strip()
                outputs = []
                for c in calls:
                    try:
                        out = tools(ToolCall(c.name, json.loads(c.arguments or "{}")))
                    except Exception as e:  # noqa: BLE001 - a failed tool is reported to the agent, which then says what it could not do
                        out = json.dumps({"error": str(e)[:300]})
                    outputs.append({"type": "function_call_output", "call_id": c.call_id, "output": out})
                resp = self.client.responses.create(input=outputs, previous_response_id=resp.id, extra_body=self.ref)
                ids.append(resp.id)
            return "NO_EVIDENCE: the search did not settle within the allowed number of steps"
        finally:
            for rid in ids:  # best effort: a response that cannot be deleted expires with the service's own retention
                try:
                    self.client.responses.delete(rid)
                except Exception:  # noqa: BLE001
                    log.warning("could not delete response %s", rid)
