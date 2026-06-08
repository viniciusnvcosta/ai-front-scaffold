"""Provider-agnostic LLM adapter.

Invariant: default to a self-hostable open model; an external API is an
isolated fallback, never a hard dependency. Swap implementations here without
touching the rest of the front.
"""

from __future__ import annotations

import os
from typing import Protocol


class LLMAdapter(Protocol):
    def complete(self, prompt: str, *, json_schema: dict | None = None) -> str: ...


class SelfHostedAdapter:
    """Primary: talks to a self-hosted endpoint (e.g. vLLM / Ollama)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def complete(self, prompt: str, *, json_schema: dict | None = None) -> str:
        raise NotImplementedError("wire up the self-hosted client")


def build_llm_adapter() -> LLMAdapter:
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
    return SelfHostedAdapter(base_url)
