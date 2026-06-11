# ai-front-scaffold

A reusable **Copier** template + canonical conventions for building **AI Fronts** —
agentic services that all share one anatomy and are assembled with the **Builder**
creational pattern. Generate a new front in seconds, then keep it in sync with the
shared conventions over time.

## Assets

- **`CLAUDE.base.md`** — the canonical, tool-agnostic conventions: scaffolding, the
  Builder pattern (Product / Builder / Concrete Builder / Director / Client),
  architecture invariants, and the Definition of Done. Imported by every generated
  repo via `@.ai-scaffold/CLAUDE.base.md`.
- **`template/`** — the Copier template that generates the standard tree with
  Product/Builder/Director already wired to the chosen recipe, plus contract,
  observability, and healthcheck hooks.

## Generate a new front

Requires [uv](https://docs.astral.sh/uv/). Copier runs through `uvx` — nothing to install globally.

```bash
uvx copier copy gh:<org>/ai-front-scaffold ./my-new-front
# prompts: project_name, module_name, recipe (collector|gateway|retriever|sink|hub|agent|api|scheduler), ...
cd my-new-front
just bootstrap   # uv sync + git init + hooks
just test
```

## Pull scaffold improvements later (the reason this is Copier, not cookiecutter)

```bash
just update      # == uvx copier update --trust
```

`copier update` re-applies the template at its newest version and three-way-merges
the changes into the existing repo — including updates to `CLAUDE.base.md`. This is
the key capability cookiecutter lacks (it only produces a one-time snapshot).

### Versioning & pinning

Releases are **SemVer git tags** on `main`; see [`CHANGELOG.md`](./CHANGELOG.md).
**`v0.2.0`** is the first stable tag (eight recipes + pluggable LLM adapter +
containerization) — the version generated repos should pin and update against.

A generated repo records the template version it was rendered from in
`.copier-answers.yml`. `just update` re-targets the **latest tag** and three-way
-merges the diff, so each front adopts "from base" improvements (e.g. graceful
shutdown, readiness probes — `v0.3.0`) deliberately, reviewing the changes before
merging. To pin a specific version explicitly:

```bash
uvx copier update --trust --vcs-ref v0.2.0
```

## Stack decision (reviewed)

| Concern            | Choice                                           | Why                                                                                                                                                       |
| ------------------ | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Project generation | **Copier** (via `uvx copier`)                    | `copier update` propagates template + base-convention changes into existing fronts; single YAML config; supports migrations. Cookiecutter only snapshots. |
| Env & dependencies | **uv**                                           | Already the standard here; fast, lockfile-based; `uvx` runs Copier without a global install.                                                              |
| Task runner        | **just**                                         | Simpler and more portable than make; recipes call `uv run`. See the generated `justfile`.                                                                 |
| Shared conventions | **`CLAUDE.base.md` carried inside the template** | Distributed and updated by Copier itself — no git submodule, no manual vendoring, no drift.                                                               |

`cookiecutter-uv` and similar are _example templates_, not generators; they are useful
references for uv+ruff+pytest wiring but are not dependencies of this scaffold.

## Recipes (front archetypes)

A recipe is a **distinct assembly order** of builder steps (the Director's job in the
Builder pattern). Each step after the mandatory `config` + `observability` base:
`input` (input contracts) · `collectors` (external integrations) · `store` (an owned,
non-SoR operational store) · `processors` (validate/normalize/score/route) · `llm`
(reason) · `output` (emit events) · `gates` (human approval). Event-driven recipes run
via `AIFront.run()`; the `api` recipe is synchronous and runs via `AIFront.serve()`.

| Recipe      | Assembly order (after base)                         | Lifecycle | Writes to system of record? |
| ----------- | --------------------------------------------------- | --------- | --------------------------- |
| `collector` | input → **collectors → processors** → llm → output  | `run`     | no                          |
| `gateway`   | input → **processors → collectors** → output        | `run`     | no                          |
| `retriever` | input → llm → **store** → processors → output       | `run`     | no                          |
| `sink`      | input → processors → **store** (terminal, no emit)  | `run`     | no                          |
| `hub`       | input → processors → output → **gates**             | `run`     | yes (the only one)          |
| `agent`     | input → **llm → processors** → output               | `run`     | no                          |
| `api`       | input → **processors → llm** → output               | `serve`   | no                          |
| `scheduler` | **processors → output** (no input; clock-triggered) | `run`     | no                          |

No two recipes share an order — that's what makes each a real recipe rather than a
rename. A few are deliberate mirror images: `collector` is **ingress-first** (collect,
then process) while `gateway` is **policy-first** (gate, then act on the channel), so its
egress is unreachable until the consent gate passes (invariant 7); `retriever` reads its
store mid-flow while `sink` is **terminal** — it ends in the store and emits nothing
(invariant 8, "single owner per store"); `api` is the only **synchronous** recipe; and
`scheduler` is the only one with **no input contracts** — its trigger is the clock.

### What each is for (beyond the original CRM domain)

- **`collector`** — ingest → process → emit. _Log/metrics shipper · price/inventory poller
  · RSS or social-listening ingester · web-scraping enrichment worker._
- **`gateway`** — owns one external egress channel; consent/eligibility gate before egress.
  _Outbound email/SMTP · SMS or WhatsApp sender with opt-in · push-notification (APNs/FCM)
  fan-out · any rate-limited, quota'd third-party egress (payment charge, shipping-label)._
- **`retriever`** — owns a vector/knowledge store; serves retrieval-augmented context.
  _RAG context service · semantic search over a doc corpus · embeddings indexer ·
  long-term agent memory._
- **`sink`** — terminal consumer; persists to a secondary (non-SoR) store, emits nothing.
  _Data-lake / warehouse loader · audit-log archiver · event-to-cold-storage writer ·
  analytics materializer._
- **`api`** — synchronous request/response endpoint (`serve`, not the event loop).
  _LLM inference / BFF endpoint · RAG-backed query API · classification/scoring service ·
  internal tool the agents call._
- **`scheduler`** — clock-triggered emitter; no input contracts, emits on a timer.
  _SLA watchdog / escalation · periodic re-enrichment or re-index kickoff · heartbeat ·
  batch-window trigger._
- **`hub`** — the single writer to the system of record; human gates on irreversible writes.
  _Order-management writer · inventory ledger with approval · account provisioning · GL
  posting behind a human gate._
- **`agent`** — input → reason → propose; never writes. _Support-ticket triage · PR/code
  review summarizer · document/contract risk analysis · incident-remediation copilot._
  An **LLM-judge/evaluator**, a **router/dispatcher**, and a **multi-agent supervisor** are
  _use-cases of `agent`_ (or of `processors`), **not** separate recipes — their assembly
  order is identical.

Add a new recipe in `template/src/<module>/front/director.py` only when the assembly
_order_ is genuinely different — otherwise reuse one of the eight. Every ordering over the
existing steps is now taken, so a genuinely new recipe means introducing a **new builder
step or lifecycle** first (as `with_store` and `serve()` did). A `scheduler` is a thin
front; if its only input is the clock, prefer deployment-time triggering (a cron sidecar
invoking it) over baking a tick loop into the process.

## Maintaining this repo

There is exactly **one** copy of the canonical conventions:
`template/.ai-scaffold/CLAUDE.base.md` (the file that ships into every generated
repo). The root-level `CLAUDE.base.md` is a **symlink** to it — convenient for
browsing, impossible to drift. Edit either path; it's the same file.

Convention changes = PR + semver tag. Generated repos adopt them deliberately via
`just update` (`copier update`), so they can review the diff before merging.
