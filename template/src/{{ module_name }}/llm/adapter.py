"""Provider-agnostic LLM adapter.

Invariant (CLAUDE.base.md #3): default to a self-hostable open model; an
external API is an isolated, opt-in fallback, never a hard dependency. Selecting
a provider is a runtime choice (env `LLM_PROVIDER`), and every external SDK is
imported lazily — importing this module never requires `anthropic` or
`langchain` to be installed. Those live behind optional extras in pyproject
(`uv sync --extra anthropic` / `--extra langchain`); the default path needs
neither.

Providers:
  self_hosted (default) — an OpenAI-compatible endpoint (vLLM / Ollama / TGI).
  anthropic             — the official Anthropic SDK (Claude).
  langchain             — any LangChain chat model (provider chosen by you).

Swap implementations here without touching the rest of the front; all fronts
depend only on the `LLMAdapter` protocol.
"""

from __future__ import annotations

import os
from typing import Protocol


class LLMAdapter(Protocol):
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> str:
        """Return the model's text completion.

        `system` sets the system prompt; `json_schema`, when given, constrains
        the output to that JSON Schema (the returned string is the JSON value).
        """
        ...


class SelfHostedAdapter:
    """Primary: an OpenAI-compatible self-hosted endpoint (e.g. vLLM / Ollama / TGI)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> str:
        raise NotImplementedError("wire up the self-hosted client")


class AnthropicAdapter:
    """Opt-in: the official Anthropic SDK (Claude).

    `anthropic` is imported lazily and is an optional extra — this class is only
    constructed when `LLM_PROVIDER=anthropic`. Reads `ANTHROPIC_API_KEY` from the
    environment via the default client (the secret is a reference, never stored
    in the repo — invariant #5).
    """

    def __init__(self, *, model: str = "claude-opus-4-8", max_tokens: int = 16000) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            import anthropic  # optional extra; imported only when this provider is selected

            self._client = anthropic.Anthropic()
        return self._client

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system is not None:
            kwargs["system"] = system
        if json_schema is not None:
            # Structured outputs: constrain the response to the schema.
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": json_schema}}
        resp = self._client_lazy().messages.create(**kwargs)
        return next((b.text for b in resp.content if b.type == "text"), "")


class LangChainAdapter:
    """Opt-in: wrap any LangChain chat model (provider-agnostic by construction).

    Lets a front reuse the LangChain ecosystem (any supported provider, tools,
    retrievers) behind the same `LLMAdapter` seam. `langchain` is an optional
    extra; the chat-model integration package for your chosen model (e.g.
    `langchain-ollama`, `langchain-anthropic`) is installed alongside it.
    """

    def __init__(self, model) -> None:
        self._model = model  # a LangChain BaseChatModel / Runnable

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_schema: dict | None = None,
    ) -> str:
        messages = []
        if system is not None:
            messages.append(("system", system))
        messages.append(("human", prompt))
        if json_schema is not None:
            import json

            structured = self._model.with_structured_output(json_schema)
            return json.dumps(structured.invoke(messages))
        return self._model.invoke(messages).content


def _build_langchain() -> LLMAdapter:
    from langchain.chat_models import init_chat_model  # optional extra

    # Self-hostable default (Ollama); set LANGCHAIN_MODEL=anthropic:claude-opus-4-8
    # to route LangChain at Claude, or any other "provider:model" string.
    model_id = os.getenv("LANGCHAIN_MODEL", "ollama:llama3.1")
    return LangChainAdapter(init_chat_model(model_id))


def build_llm_adapter() -> LLMAdapter:
    """Construct the adapter for the configured provider (self-hostable default)."""
    provider = os.getenv("LLM_PROVIDER", "self_hosted").lower()
    if provider == "self_hosted":
        return SelfHostedAdapter(os.getenv("LLM_BASE_URL", "http://localhost:8000/v1"))
    if provider == "anthropic":
        return AnthropicAdapter(model=os.getenv("LLM_MODEL", "claude-opus-4-8"))
    if provider == "langchain":
        return _build_langchain()
    raise ValueError(
        f"unknown LLM_PROVIDER {provider!r}; expected one of: self_hosted, anthropic, langchain"
    )
