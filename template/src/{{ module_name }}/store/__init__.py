"""Owned operational store (vector / knowledge / archive).

Invariant: each store has a SINGLE owner front (see CLAUDE.base.md, invariant 8).
This is NOT the system of record — only the `hub` writes that. It is an
operational store this front owns end to end (a vector index for a `retriever`,
a data lake / audit log for a `sink`). Keep it behind this adapter so the rest
of the front never touches the client directly, and default to a self-hostable
backend (mirrors the LLM adapter's self-hostable-first rule).
"""

from __future__ import annotations

import os
from typing import Protocol


class StoreAdapter(Protocol):
    def upsert(self, key: str, value: object) -> None: ...
    def query(self, query: object, *, top_k: int = 5) -> list: ...


class SelfHostedStore:
    """Primary: a self-hosted store (e.g. pgvector / Qdrant / OpenSearch / S3)."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def upsert(self, key: str, value: object) -> None:
        raise NotImplementedError("wire up the self-hosted store client")

    def query(self, query: object, *, top_k: int = 5) -> list:
        raise NotImplementedError("wire up the self-hosted store client")


def build_store() -> StoreAdapter:
    dsn = os.getenv("STORE_DSN", "postgresql://localhost:5432/store")
    return SelfHostedStore(dsn)
