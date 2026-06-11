"""The Product of the Builder pattern: an assembled AI Front.

This file comes from the scaffold base and is normally stable. Each front
fills the parts via its ConcreteBuilder; it does not edit this class.
"""

from __future__ import annotations

import logging
import signal
import threading
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
    # Lifecycle machinery (k8s graceful shutdown). Not part of the builder wiring,
    # so kept out of __init__ and repr — see run()/serve()/shutdown() below.
    _stop: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def healthcheck(self) -> bool:
        """Liveness signal: the front is assembled and wired.

        Cheap and dependency-free — answers "is the process up and coherent?".
        See readiness() for the "can it serve traffic right now?" check.
        """
        return bool(self.name) and self.config is not None

    def readiness(self) -> bool:
        """Readiness signal: the front can serve traffic right now.

        Liveness (healthcheck) plus the external dependencies this front owns:
        every attached resource that exposes a ``ready()`` or ``ping()`` probe
        must report healthy (e.g. Redis reachable, contracts loaded). A front
        with no probing resources is ready as soon as it is live — so the
        default generated project stays ready out of the box. Concrete fronts
        make readiness meaningful by giving their resources a ``ready()``/
        ``ping()`` method.
        """
        if not self.healthcheck():
            return False
        for resource in self._resources():
            probe = getattr(resource, "ready", None) or getattr(resource, "ping", None)
            if probe is None:
                continue
            try:
                if not probe():
                    return False
            except Exception:  # an unreachable dependency is "not ready", not a crash
                log.warning("AIFront '%s' readiness probe failed on %r", self.name, resource)
                return False
        return True

    # --- graceful shutdown -------------------------------------------------

    def request_stop(self) -> None:
        """Signal the run loop to wind down (idempotent)."""
        self._stop.set()

    def is_stopping(self) -> bool:
        """True once a stop has been requested (SIGTERM/SIGINT or request_stop)."""
        return self._stop.is_set()

    def _resources(self):
        """Every attached resource, in wiring order, for probe/close fan-out."""
        yield from self.inputs
        yield from self.collectors
        yield from self.processors
        yield from self.outputs
        yield from self.gates
        if self.store is not None:
            yield self.store

    def _install_signal_handlers(self) -> None:
        """Route SIGTERM/SIGINT to a clean stop. No-op off the main thread.

        k8s sends SIGTERM on pod teardown (rolling update); without this,
        Redis Streams consumers and the dispatch worker lose acks/checkpoints.
        signal.signal only works on the main thread and may be unavailable in
        some runtimes, hence the guards.
        """
        if threading.current_thread() is not threading.main_thread():
            return

        def _handle(signum, _frame):
            log.info("AIFront '%s' received signal %s; requesting graceful stop", self.name, signum)
            self.request_stop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, _handle)
            except (ValueError, OSError):  # not main thread / unsupported platform
                pass

    def shutdown(self) -> None:
        """Close owned resources once, in wiring order (idempotent).

        Calls ``close()`` on any attached resource that has one; resources
        without it are skipped. Safe to call multiple times (run()'s finally
        and an explicit caller may both invoke it).
        """
        if self._closed:
            return
        self._closed = True
        for resource in self._resources():
            close = getattr(resource, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # one resource failing must not abort the rest
                    log.exception("AIFront '%s' failed to close %r", self.name, resource)

    def run(self) -> None:
        """Standardized lifecycle entrypoint for event-driven fronts.

        Installs SIGTERM/SIGINT handlers, then blocks until a stop is requested
        and closes resources cleanly on the way out. Concrete fronts attach
        their loop/handlers via the builder steps and poll is_stopping(); the
        default lifecycle is an idle wait that exits cleanly on signal.
        """
        if not self.healthcheck():
            raise RuntimeError(f"AIFront '{self.name}' failed healthcheck on startup")
        self._install_signal_handlers()
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
        try:
            self._stop.wait()
        finally:
            self.shutdown()

    def serve(self) -> None:
        """Synchronous request/response lifecycle entrypoint.

        Used by `api`/bff fronts instead of run(): there is no event loop, the
        front handles requests and returns responses. Installs SIGTERM/SIGINT
        handlers so a pod teardown flips is_stopping(); the concrete server
        runtime drives requests, must honor is_stopping(), and should call
        shutdown() on exit to release resources cleanly.
        """
        if not self.healthcheck():
            raise RuntimeError(f"AIFront '{self.name}' failed healthcheck on startup")
        self._install_signal_handlers()
        log.info(
            "AIFront '%s' serving (inputs=%d, processors=%d, outputs=%d)",
            self.name,
            len(self.inputs),
            len(self.processors),
            len(self.outputs),
        )
