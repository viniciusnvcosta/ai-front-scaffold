# CLAUDE.base.md — Canonical "AI Front" Conventions

> **What this file is.** The single, reusable source of conventions for any **AI Front** (an agentic service) in this organization. Every repository keeps a thin `CLAUDE.md` at its root that **imports** this file via `@` and adds only project-specific memory. Keep this file tool-agnostic, project-agnostic, and high-signal.
>
> **How Claude Code consumes it.** The root `CLAUDE.md` is read at the start of every session and survives `/compact`. `@path` imports load at launch (context cost), support up to 5 recursive levels, and are **not evaluated inside code blocks** — so the examples below sit in code fences and are safe to document. Keep each memory file focused and short.
>
> **How this file stays current across repos.** This scaffold is distributed as a **Copier** template. Generated repos pull improvements to this file (and the rest of the scaffold) with `copier update` — no manual copying, no submodule drift.

---

## 1. Core idea: every AI Front is the same Product, assembled differently

All fronts share the **same anatomy**. What differs between them is _which parts_ are filled and _with what_. That is the textbook use case for the creational **Builder** pattern: one construction process (step by step, in a fixed order) produces different representations of the same complex product.

### Builder pattern → AI Front mapping

| Builder role            | Here                   | Responsibility                                                                                                     |
| ----------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Product**             | `AIFront`              | the assembled service: config + inputs + collectors + processors + llm + outputs + gates + observability + runtime |
| **Builder (interface)** | `AIFrontBuilder`       | declares the construction steps common to all fronts                                                               |
| **Concrete Builders**   | one per front          | implement the steps differently per front                                                                          |
| **Director**            | `FrontDirector`        | encapsulates the assembly _recipes_ (`collector`, `hub`, `agent`)                                                  |
| **Client**              | `src/<module>/main.py` | picks a builder, asks the director for a recipe, gets a ready `AIFront`                                            |

Practical payoff: a new front does **not** reinvent lifecycle, healthcheck, contract validation, observability, or wiring. It implements only the parts that make it distinct. Fronts stay consistent, testable, and generatable.

---

## 2. Canonical scaffolding (every front follows this tree)

```text
<ai-front>/
├── CLAUDE.md                      # thin pointer: imports @.ai-scaffold/CLAUDE.base.md + project memory
├── README.md                      # project-specific docs (scope + roadmap; one per repo)
├── .ai-scaffold/
│   └── CLAUDE.base.md             # this file (kept in sync via `copier update`)
├── .copier-answers.yml            # records template answers (enables `copier update`)
├── contracts/                     # versioned schemas this front consumes/produces
├── pyproject.toml                 # uv-managed
├── justfile                       # task runner recipes
├── Dockerfile
├── src/<module>/
│   ├── front/
│   │   ├── product.py             # AIFront (stable; from base)
│   │   ├── builder.py             # ConcreteBuilder for THIS front
│   │   └── director.py            # assembly recipes (stable; from base)
│   ├── config/                    # config loading + secret references (never secrets)
│   ├── inputs/                    # event consumers / endpoints / input contracts
│   ├── collectors/                # external integrations (APIs, scrapers)
│   ├── processors/                # validators, normalizers, scoring, routing
│   ├── llm/                       # provider-agnostic adapter (self-hostable first)
│   ├── outputs/                   # event emitters / writers (output contracts)
│   ├── gates/                     # human decision points
│   ├── observability/             # metrics, logs, traces
│   └── main.py                    # Client: wires director + builder
├── tests/
│   ├── contract_tests/            # validate I/O against contracts/
│   └── unit/
└── ops/
    ├── compose.fragment.yml       # service definition, merged by the platform layer
    └── healthcheck.py
```

Each `src/<module>` subpackage maps **1:1 to a builder step**. A front fills the directories that characterize it densely and leaves the rest thin (e.g., a `collector` front has rich `collectors/` and empty `gates/`; a `hub` front has rich `outputs/` + `gates/`; an `agent` front has rich `processors/` + `llm/`).

---

## 3. The Builder interface (mandatory steps, fixed order)

```python
# src/<module>/front/product.py  (from base; stable)
from dataclasses import dataclass, field

@dataclass
class AIFront:
    name: str
    config: dict = field(default_factory=dict)
    inputs: list = field(default_factory=list)        # input contracts / consumers
    collectors: list = field(default_factory=list)    # external sources
    processors: list = field(default_factory=list)    # validation / normalization / scoring / routing
    llm_adapter: object | None = None                 # provider-agnostic; self-hostable first
    outputs: list = field(default_factory=list)       # emitters / writers
    gates: list = field(default_factory=list)         # human decision points
    observability: object | None = None

    def healthcheck(self) -> bool: ...
    def run(self) -> None: ...                         # standardized lifecycle


# src/<module>/front/builder.py  (interface; each front implements its own)
from abc import ABC, abstractmethod

class AIFrontBuilder(ABC):
    @abstractmethod
    def reset(self) -> None: ...
    @abstractmethod
    def with_config(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def with_input_contracts(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def with_collectors(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def with_processors(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def with_llm_adapter(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def with_output_contracts(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def with_human_gates(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def with_observability(self) -> "AIFrontBuilder": ...
    @abstractmethod
    def build(self) -> "AIFront": ...
```

```python
# src/<module>/front/director.py  (assembly recipes; from base)
class FrontDirector:
    def __init__(self, builder: "AIFrontBuilder") -> None:
        self._b = builder

    def _base(self) -> None:                 # steps common to ALL fronts
        self._b.reset()
        self._b.with_config()
        self._b.with_observability()

    def build_collector_front(self) -> "AIFront":   # ingest → process → emit
        self._base()
        self._b.with_input_contracts()
        self._b.with_collectors()
        self._b.with_processors()
        self._b.with_llm_adapter()
        self._b.with_output_contracts()
        return self._b.build()

    def build_hub_front(self) -> "AIFront":         # single writer to the system of record
        self._base()
        self._b.with_input_contracts()
        self._b.with_processors()
        self._b.with_output_contracts()
        self._b.with_human_gates()
        return self._b.build()

    def build_agent_front(self) -> "AIFront":       # input → reason → propose
        self._base()
        self._b.with_input_contracts()
        self._b.with_llm_adapter()
        self._b.with_processors()
        self._b.with_output_contracts()
        return self._b.build()
```

```python
# src/<module>/main.py  (Client)
from .front.builder import ConcreteFrontBuilder
from .front.director import FrontDirector

front = FrontDirector(ConcreteFrontBuilder()).build_collector_front()
front.run()
```

> **Rule:** steps always run in the director's order. `with_config` and `with_observability` are mandatory in every recipe. A front that does not need a step (e.g., a collector with no human gates) simply omits it from the recipe — it does not implement an empty step with side effects.

---

## 4. Architecture invariants (apply to every repo — do not violate)

1. **Single writer to the system of record.** Only the `hub` front writes to the shared system of record. Other fronts emit events/proposals and never hold write credentials to it.
2. **Contracts first, versioned.** All inter-front communication goes through a versioned schema in `contracts/` (sourced from the platform layer). Changing a contract = PR + version bump. Contract tests are mandatory.
3. **Provider-agnostic LLM, self-hostable first.** LLM access sits behind an adapter. Default to a self-hostable open model; an external API is an isolated fallback, never a hard dependency.
4. **Risk gates are always human.** Irreversible or high-impact actions are routed through a human gate, never auto-executed.
5. **No secrets in the repo.** `config/` holds only _references_ to secrets; values live in a secret manager. CI fails if a secret is detected.
6. **Idempotency.** Event consumers are idempotent (natural key, e.g. `event_id`). Reprocessing causes no duplicate effect.

---

## 5. Definition of Done (what Claude Code must ensure before finishing a task)

- [ ] The front is assembled via `Director + ConcreteBuilder`; `main.py` does no ad-hoc wiring.
- [ ] Inputs and outputs validate against the schemas in `contracts/` (contract tests pass).
- [ ] `healthcheck()` is implemented and exposed; `ops/compose.fragment.yml` is updated.
- [ ] No write credential to the system of record exists outside the `hub` front.
- [ ] Secrets are referenced only; secret scanning in CI is green.
- [ ] LLM access is behind the adapter (self-hostable primary; isolated fallback).
- [ ] Observability: structured logs and metrics are emitted.
- [ ] Unit tests cover the front's distinctive `processors`/`collectors`.
- [ ] The project `README.md` reflects current scope, roadmap, and success criteria.

---

## 6. Canonical task runner recipes (each repo keeps equivalents in its justfile)

```bash
just bootstrap    # uv sync + git init + install hooks
just dev          # run the front locally against the platform layer
just test         # unit + contract tests
just contracts    # validate schemas against the pinned platform version
just lint         # ruff + secret scan
just update       # copier update — pull scaffold/base improvements into this repo
```

---

## 7. Creating a new front (future projects)

1. `uvx copier copy <scaffold-url> <dest>` and answer the prompts (name, module, recipe, etc.).
2. Pick the director recipe (`collector` | `hub` | `agent`) — or add a new recipe only if the assembly order is genuinely different.
3. Implement the `ConcreteBuilder`, filling only the relevant steps.
4. Define/extend the shared `contracts/` and pin the version.
5. Write the project `README.md` (scope + roadmap + success criteria).
6. Keep the root `CLAUDE.md` as a thin pointer (see the generated template).
7. Later, run `just update` (i.e. `copier update`) to absorb scaffold improvements.
