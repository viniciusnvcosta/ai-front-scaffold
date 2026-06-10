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
# prompts: project_name, module_name, recipe (collector|hub|agent), ...
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
`input` (input contracts) · `collectors` (external integrations) · `processors`
(validate/normalize/score/route) · `llm` (reason) · `output` (emit events) ·
`gates` (human approval).

| Recipe      | Assembly order (after base)                  | Writes to system of record? |
| ----------- | -------------------------------------------- | --------------------------- |
| `collector` | input → **collectors → processors** → llm → output | no                    |
| `gateway`   | input → **processors → collectors** → output | no                          |
| `hub`       | input → processors → output → **gates**      | yes (the only one)          |
| `agent`     | input → **llm → processors** → output         | no                          |

No two recipes share an order — that's what makes each a real recipe rather than a
rename. Note `collector` and `gateway` are mirror images: `collector` is **ingress-first**
(collect, then process), `gateway` is **policy-first** (gate, then act on the channel), so
its egress is structurally unreachable until the eligibility/consent gate has passed
(invariant 7, "single channel owner").

### What each is for (beyond the original CRM domain)

- **`collector`** — ingest → process → emit. _Log/metrics shipper · price/inventory poller
  · RSS or social-listening ingester · web-scraping enrichment worker._
- **`gateway`** — owns one external egress channel; consent/eligibility gate before egress.
  _Outbound email/SMTP · SMS or WhatsApp sender with opt-in · push-notification (APNs/FCM)
  fan-out · any rate-limited, quota'd third-party egress (payment charge, shipping-label)._
- **`hub`** — the single writer to the system of record; human gates on irreversible writes.
  _Order-management writer · inventory ledger with approval · account provisioning · GL
  posting behind a human gate._
- **`agent`** — input → reason → propose; never writes. _Support-ticket triage · PR/code
  review summarizer · document/contract risk analysis · incident-remediation copilot._
  An **LLM-judge/evaluator**, a **router/dispatcher**, and a **multi-agent supervisor** are
  _use-cases of `agent`_ (or of `processors`), **not** separate recipes — their assembly
  order is identical.

Add a new recipe in `template/src/<module>/front/director.py` only when the assembly
_order_ is genuinely different — otherwise reuse one of the four.

## Candidate archetypes (backlog)

Ranked by demand and by how much new machinery they require. The bar is the same as
above: a candidate earns a recipe only if its assembly order is genuinely new (which here
means it needs a **new builder step or lifecycle** — every order over the _existing_ steps
is already taken).

| Priority | Candidate          | Shape                                              | What it needs first |
| -------- | ------------------ | -------------------------------------------------- | ------------------- |
| **P0**   | `retriever`/memory | owns a vector/knowledge store; serves RAG context  | a new `with_store` step + a "single owner per store" invariant (mirrors hub's single-writer & gateway's single-channel) |
| **P1**   | `sink`/archiver    | terminal consumer; writes a secondary non-SoR store (data lake, audit) | the _same_ `with_store` step — rides P0 |
| **P1**   | `api`/bff          | synchronous request/response instead of the event-loop `run()` | a distinct `serve()` lifecycle on `AIFront` (touches `product.py`) |
| **P2**   | `scheduler`/cron   | time-driven emitter; no input contracts            | nothing structural, but often better modeled as deployment-time triggering of a `collector` |

`with_store` is the highest-leverage next step: it unlocks **both** `retriever`
(read-heavy) and `sink` (write-heavy) and introduces one clean new invariant alongside the
existing single-writer (hub) and single-channel (gateway) ones. The synchronous `api`/bff
is just as common but its second-lifecycle prerequisite is heavier and risks diluting the
scaffold's event-driven identity, so it sits behind the store work. `scheduler` needs no
new machinery but is frequently infrastructure (a cron sidecar invoking a `collector`)
rather than a front in its own right.

## Maintaining this repo

There is exactly **one** copy of the canonical conventions:
`template/.ai-scaffold/CLAUDE.base.md` (the file that ships into every generated
repo). The root-level `CLAUDE.base.md` is a **symlink** to it — convenient for
browsing, impossible to drift. Edit either path; it's the same file.

Convention changes = PR + semver tag. Generated repos adopt them deliberately via
`just update` (`copier update`), so they can review the diff before merging.
