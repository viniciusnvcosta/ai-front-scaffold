"""The Product of the Builder pattern: an assembled AI Front.

This file comes from the scaffold base and is normally stable. Each front
fills the parts via its ConcreteBuilder; it does not edit this class.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class AIFront:
    name: str
    config: dict = field(default_factory=dict)
    inputs: list = field(default_factory=list)
    collectors: list = field(default_factory=list)
    processors: list = field(default_factory=list)
    llm_adapter: object | None = None
    outputs: list = field(default_factory=list)
    gates: list = field(default_factory=list)
    store: object | None = None  # owned operational store (NOT the system of record)
    observability: object | None = None

    def healthcheck(self) -> bool:
        """Liveness/readiness signal used by ops/healthcheck.py."""
        return bool(self.name) and self.config is not None

    def run(self) -> None:
        """Standardized lifecycle entrypoint for event-driven fronts.

        Concrete fronts attach their loop/handlers via the builder steps;
        the default lifecycle just validates wiring and yields control.
        """
        if not self.healthcheck():
            raise RuntimeError(f"AIFront '{self.name}' failed healthcheck on startup")
        log.info(
            "AIFront '%s' started (inputs=%d, collectors=%d, processors=%d, outputs=%d, gates=%d, store=%s)",
            self.name,
            len(self.inputs),
            len(self.collectors),
            len(self.processors),
            len(self.outputs),
            len(self.gates),
            self.store is not None,
        )

    def serve(self) -> None:
        """Synchronous request/response lifecycle entrypoint.

        Used by `api`/bff fronts instead of run(): there is no event loop, the
        front handles requests and returns responses. The concrete front attaches
        its endpoint handler via the builder steps; the default lifecycle validates
        wiring and yields control to the server runtime.
        """
        if not self.healthcheck():
            raise RuntimeError(f"AIFront '{self.name}' failed healthcheck on startup")
        log.info(
            "AIFront '%s' serving (inputs=%d, processors=%d, outputs=%d)",
            self.name,
            len(self.inputs),
            len(self.processors),
            len(self.outputs),
        )
