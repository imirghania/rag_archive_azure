"""Foundry model adapters (Azure OpenAI API of the AI Services account, Entra authentication): the chat roles, the second
reader and the embeddings. The deployment of each role is read from settings, so moving a role to another model is one line."""
from __future__ import annotations

import base64
from typing import Any

from pydantic import BaseModel

from docai.contracts.llm import VlmOutput
from docai.core.settings import Settings

API_VERSION = "2025-04-01-preview"
_ROLE_TO_FIELD = {
    "router": "router", 
    "segmentation": "segmentation", 
    "metadata": "metadata", 
    "verifier": "verifier", 
    "answer_agent": "answer_agent"
    }


def make_client(settings: Settings, credential: Any = None):
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import AzureOpenAI

    provider = get_bearer_token_provider(
        credential or DefaultAzureCredential(), 
        "https://cognitiveservices.azure.com/.default"
        )
    return AzureOpenAI(azure_endpoint=settings.azure.foundry_endpoint, 
                    azure_ad_token_provider=provider, 
                    api_version=API_VERSION, 
                    max_retries=5)


class FoundryChat:
    def __init__(self, settings: Settings, client: Any = None) -> None:
        self.s, self.client = settings, client or make_client(settings)

    def complete_json(self, role: str, system: str, 
                    user: str, schema: type[BaseModel]) -> BaseModel:
        """Structured output: the schema is the JSON contract the prompt describes, enforced by the service."""
        deployment = getattr(self.s.models, _ROLE_TO_FIELD[role])
        r = self.client.beta.chat.completions.parse(model=deployment, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                                                    response_format=schema)
        msg = r.choices[0].message
        if msg.parsed is None:
            raise ValueError(f"the {role} model returned no valid {schema.__name__}: {msg.refusal or msg.content!r}")
        return msg.parsed


class FoundryVision:
    """The second reader. It receives the crop and a language hint, and nothing else: there is no parameter for the OCR text."""

    def __init__(self, settings: Settings, client: Any = None) -> None:
        self.s, self.client = settings, client or make_client(settings)

    def transcribe(self, crop: bytes, *, lang_hint: str, line_key: str) -> VlmOutput:
        from docai.resources import prompts

        url = "data:image/png;base64," + base64.b64encode(crop).decode()
        r = self.client.beta.chat.completions.parse(
            model=self.s.models.second_reader, response_format=VlmOutput,
            messages=[
                {
                    "role": "system", 
                    "content": prompts.render("second_reader", lang_hint=lang_hint)
                    },
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": "Transcribe this line."}, 
                        {"type": "image_url", "image_url": {"url": url, "detail": "high"}}
                        ]
                    }
                ])
        out = r.choices[0].message.parsed
        if out is None:
            raise ValueError(f"the second reader returned no valid reading for {line_key}")
        return out


class FoundryEmbedder:
    BATCH = 64

    def __init__(self, settings: Settings, client: Any = None) -> None:
        self.s, self.client = settings, client or make_client(settings)
        self.dimensions = settings.models.embedding_dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH):
            r = self.client.embeddings.create(
                model=self.s.models.embeddings, 
                input=[t or " " for t in texts[i:i + self.BATCH]], 
                dimensions=self.dimensions)
            out += [d.embedding for d in sorted(r.data, key=lambda d: d.index)]
        return out
