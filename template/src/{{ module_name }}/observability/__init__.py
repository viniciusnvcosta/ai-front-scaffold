"""Structured logging + metrics hooks."""

from __future__ import annotations

import logging


class Observability:
    def __init__(self, service: str) -> None:
        self.service = service
        self.log = logging.getLogger(service)


def build_observability(service: str) -> "Observability":
    return Observability(service)
