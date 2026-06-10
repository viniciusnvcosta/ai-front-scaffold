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

| Recipe      | Shape                                                               | Writes to system of record? |
| ----------- | ------------------------------------------------------------------- | --------------------------- |
| `collector` | ingest → process → emit                                             | no                          |
| `gateway`   | owns one external channel; consent gate before egress; emits events | no                          |
| `hub`       | single writer; enforces human gates                                 | yes (the only one)          |
| `agent`     | input → reason → propose                                            | no                          |

`gateway` sits between `collector` and `hub`: heavy inputs _and_ outputs, but it
emits events instead of writing to the system of record. Its defining trait is the
eligibility/consent gate in `processors/` that runs ahead of any outbound message —
see invariant 7 ("single channel owner") in `CLAUDE.base.md`.

Add a new recipe in `template/src/<module>/front/director.py` only when the assembly
_order_ is genuinely different — otherwise reuse one of the four.

## Maintaining this repo

There is exactly **one** copy of the canonical conventions:
`template/.ai-scaffold/CLAUDE.base.md` (the file that ships into every generated
repo). The root-level `CLAUDE.base.md` is a **symlink** to it — convenient for
browsing, impossible to drift. Edit either path; it's the same file.

Convention changes = PR + semver tag. Generated repos adopt them deliberately via
`just update` (`copier update`), so they can review the diff before merging.
