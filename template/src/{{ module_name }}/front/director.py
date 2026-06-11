"""The Director of the Builder pattern: assembly recipes.

Recipes define the ORDER of construction steps. with_config and
with_observability are mandatory in every recipe.
"""

from __future__ import annotations

from .builder import AIFrontBuilder
from .product import AIFront


class FrontDirector:
    def __init__(self, builder: AIFrontBuilder) -> None:
        self._b = builder

    def _base(self) -> None:
        self._b.reset()
        self._b.with_config()
        self._b.with_observability()

    def build_collector_front(self) -> AIFront:
        """ingest -> process -> emit (no writes to the system of record)."""
        self._base()
        self._b.with_input_contracts()
        self._b.with_collectors()
        self._b.with_processors()
        self._b.with_llm_adapter()
        self._b.with_output_contracts()
        return self._b.build()

    def build_gateway_front(self) -> AIFront:
        """ingest -> gate -> external channel -> emit status (no SoR write).

        Owns a single external channel (messaging, email, telephony). Heavy
        inputs AND outputs, but NEVER writes to the system of record: it emits
        events/status. The ORDER is the point: `processors` (the eligibility/
        consent gate, rate limit, retry/DLQ) runs BEFORE `collectors` (the
        channel adapter), so egress is structurally unreachable until the gate
        has passed. This is the inverse of the collector's ingress-first order
        (collect, then process) and is what makes gateway a distinct recipe.
        """
        self._base()
        self._b.with_input_contracts()
        self._b.with_processors()  # eligibility/consent gate (MUST precede egress) + rate limit + retry/DLQ
        self._b.with_collectors()  # the owned external channel adapter (egress/ingress)
        self._b.with_output_contracts()
        return self._b.build()

    def build_retriever_front(self) -> AIFront:
        """query/index -> embed -> store -> rerank -> serve context (no SoR write).

        Owns a single vector/knowledge store (invariant 8). Embeds the query or
        document (llm), reads/writes its OWN store, re-ranks/formats (processors),
        and emits the retrieved context. The store sits between llm and processors,
        which is an order no other recipe has.
        """
        self._base()
        self._b.with_input_contracts()
        self._b.with_llm_adapter()  # embeddings (+ optional generation)
        self._b.with_store()  # the owned knowledge/vector store
        self._b.with_processors()  # chunking / re-ranking / formatting
        self._b.with_output_contracts()
        return self._b.build()

    def build_sink_front(self) -> AIFront:
        """consume -> normalize -> persist to a secondary store; terminal (no emit, no SoR).

        Terminal consumer: it is the only recipe that ends in `with_store` and
        omits `with_output_contracts` entirely — it persists to its OWN store
        (data lake / audit log, invariant 8) and emits nothing onward.
        """
        self._base()
        self._b.with_input_contracts()
        self._b.with_processors()  # validate / normalize / partition
        self._b.with_store()  # the owned archive / data-lake store
        return self._b.build()

    def build_hub_front(self) -> AIFront:
        """single writer to the system of record; enforces human gates."""
        self._base()
        self._b.with_input_contracts()
        self._b.with_processors()
        self._b.with_output_contracts()
        self._b.with_human_gates()
        return self._b.build()

    def build_agent_front(self) -> AIFront:
        """input -> reason -> propose (returns proposals; never writes)."""
        self._base()
        self._b.with_input_contracts()
        self._b.with_llm_adapter()
        self._b.with_processors()
        self._b.with_output_contracts()
        return self._b.build()

    def build_api_front(self) -> AIFront:
        """request -> validate -> reason -> response; SYNCHRONOUS (serve lifecycle, no SoR write).

        Unlike the event-driven recipes, the assembled front is driven by
        AIFront.serve() (request/response), not run(). Order is
        input -> processors -> llm -> output, distinct from every other recipe.
        """
        self._base()
        self._b.with_input_contracts()  # request schema / endpoints
        self._b.with_processors()  # auth / validation / routing
        self._b.with_llm_adapter()  # reason (inference / RAG-backed responses)
        self._b.with_output_contracts()  # response schema
        return self._b.build()

    def build_scheduler_front(self) -> AIFront:
        """tick -> decide what's due -> emit (clock-triggered, no SoR write).

        The only recipe with NO with_input_contracts: its trigger is the clock,
        not a consumed event. On each tick `processors` decide what is due
        (cron expression, SLA watchdog, heartbeat) and `output` emits the
        resulting events. Driven by run() as a tick loop.
        """
        self._base()
        self._b.with_processors()  # evaluate schedules / SLAs / due items on each tick
        self._b.with_output_contracts()
        return self._b.build()
