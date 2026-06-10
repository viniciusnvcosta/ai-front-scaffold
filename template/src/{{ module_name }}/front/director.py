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
        """ingest <-> external channel; enforce eligibility/consent before egress.

        Owns a single external channel (messaging, email, telephony). Heavy
        inputs AND outputs, but NEVER writes to the system of record: it emits
        events/status. The defining trait is the consent/eligibility gate that
        sits in `processors` ahead of any outbound message.
        """
        self._base()
        self._b.with_input_contracts()
        self._b.with_collectors()  # the external channel adapter
        self._b.with_processors()  # consent gate, rate limit, retry/DLQ, reply classification
        self._b.with_llm_adapter()  # optional: classify inbound replies
        self._b.with_output_contracts()
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
