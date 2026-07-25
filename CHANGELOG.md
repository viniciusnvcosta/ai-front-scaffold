# Changelog

All notable changes to **`ai-front-scaffold`** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Generated repos pin a scaffold tag in `.copier-answers.yml` and adopt changes
deliberately with `just update` (`copier update`), reviewing the diff before
merging. A **MINOR** bump means new "from base" capabilities flow into child
repos on their next update; read the entry before running it.

## [Unreleased]

## [0.4.0]

Delivery-workflow standard — "from base", reaches every front on `copier update`.
Upstreams into the template what the three mesh app repos
(`campaign-manager`, `bitrix-orchestrator`, `lead-enrichment-engine`) had already
received by hand over the last day, so future fronts are born with it and
current ones adopt it deliberately via `just update`.

### Added
- **§8 "Delivery workflow & quality gates" in `CLAUDE.base.md`.** Documents the
  orchestrator + fresh-subagent execution model, the gates a task must pass
  (tests ≥90% coverage, lint, contracts, Conventional Commits with no
  generated-with footer, PR-based flow only), the docs layout
  (`docs/adr/`, `docs/plans/`, `CHANGELOG.md`, `CONTEXT.md`/`docs/agents/`),
  and the security-review cadence (differential-review per PR,
  insecure-defaults per release, semgrep per release).
- **Coverage gate in the generated `justfile`.** `test` now runs
  `pytest -q --cov=src/{{ module_name }} --cov-fail-under=90` (the flag lives in
  the justfile recipe, never in `[tool.pytest.ini_options] addopts`, because
  `just contracts` runs only the `tests/contract_tests` subset and a global
  addopts gate would fail that otherwise-green subset run). New `check: lint
  test contracts` recipe aggregates the full local/CI gate in one command.
  `pytest-cov>=7.1.0` added to the `dev` dependency group.
- **CI trio template**, byte-copied from the mesh app repos' shared donor
  (`.tool-versions`, `tools/ci-install-tools.sh`, `azure-pipelines.yml`):
  a `Gate` stage that installs the pinned toolchain (just/uv/gitleaks) and
  runs exactly `just check`, with `uv`- and tool-cache steps keyed off
  `uv.lock` / `.tool-versions`. No project-specific placeholders — copied
  as plain (non-`.jinja`) files.
- **`uv.lock` now tracked** in generated repos: the template's `.gitignore` no
  longer ignores it. `uv sync --frozen` in the new CI Gate (and its cache key)
  requires the lockfile to be committed — an untracked `uv.lock` made the CI
  step and the cache non-reproducible. `.coverage` (the pytest-cov artifact
  the new gate produces) is now ignored instead.
- **`test_builder_interface.py.jinja`**: a new unit test calling every `with_*`
  step directly on the Concrete Builder, independent of the recipe's assembly
  order. Needed to keep the new gate accurate: `build()` alone only exercises
  the steps THIS recipe's director calls, so thinner recipes (`scheduler`: 6 of
  9 steps; `sink`: 6 of 9) undershot 90% purely because their by-design no-op
  steps went unexercised (`scheduler` measured 89.89% before this test). All
  eight recipes now clear the gate with margin (91.7-91.8%).

### Notes
- Recipe construction order is unchanged; no builder steps or public
  signatures were altered.
- The zero-dependency default project (`dependencies = []`) passes the new
  `just test` (coverage-gated) and `just contracts` on all eight recipes —
  verified by generating each and running both. `just lint` currently fails
  on a freshly generated project independent of this release (ruff, pinned
  here at `>=0.6`, resolves to 0.16.0 today and flags ~25 pre-existing
  findings — e.g. `RUF100`/`BLE001`/`UP037` in `builder.py`/`product.py`/
  `healthcheck.py` — that 0.3.0 already has; reproduced identically on a
  vanilla `v0.3.0` render). Out of scope for this release; tracked as a
  follow-up (pin an older ruff or fix the flagged lines).

## [0.3.0]

K8s readiness work — "from base", reaches every front on `copier update`.

### Added
- **Graceful shutdown.** `AIFront.run()`/`serve()` install SIGTERM/SIGINT handlers
  that flip an internal stop flag; `run()` blocks until stopped and closes owned
  resources via `shutdown()` (idempotent, duck-typed `close()`). New public
  surface: `request_stop()`, `is_stopping()`, `shutdown()`. Prevents Redis
  Streams consumers / dispatch workers from losing acks/checkpoints on a k8s
  rolling update.
- **Readiness separate from liveness.** `AIFront.readiness()` checks owned
  dependencies (any resource exposing `ready()`/`ping()`) on top of liveness;
  `ops/healthcheck.py --readiness` wires it to the k8s readinessProbe. The bare
  script stays liveness (Docker HEALTHCHECK / livenessProbe).
- **Multiprocess `gateway` (one image, two deployables).** `APP_ROLE` (`api` |
  `worker`, default `worker`) selects `serve()` vs `run()` in `main.py`;
  `ops/compose.fragment.yml` emits `<slug>-api` and `<slug>-worker` services for
  the `gateway` recipe (single service for all others).
- **Batch-metrics convention** in `CLAUDE.base.md`: batch/short-lived fronts push
  to a Pushgateway or expose an ephemeral `/metrics` instead of registering a
  standing Prometheus scrape target (which would sit permanently DOWN).
- New jinja unit tests: `test_product_lifecycle`, `test_app_role`,
  `test_compose_fragment`, `test_healthcheck_modes`.

### Notes
- Recipe construction **order is unchanged** — `test_director_recipes` still
  passes; no builder steps or public signatures were altered.
- Default generated project keeps `dependencies = []` (zero-dep); no new runtime
  or test dependencies were introduced.

## [0.2.0]

First stable, taggable scaffold — the version child repos pin and update against.

### Added
- `gateway` recipe and the full set of **eight order-distinct archetypes**
  (`collector`, `gateway`, `retriever`, `sink`, `hub`, `agent`, `api`,
  `scheduler`); no two share a builder step order.
- **Pluggable `LLMAdapter`**: self-hosted default (OpenAI-compatible), with
  `anthropic` and `langchain` as lazy-imported optional extras — importing the
  module never pulls an external SDK and the default path has zero deps.
- Containerization: `Dockerfile`, `ops/compose.fragment.yml`, `ops/healthcheck.py`.
- Jinja unit tests locking recipe construction order, adapter dispatch, and store
  defaults; CI matrix renders and tests all eight recipes.

## [0.1.0]

### Added
- Initial Copier template: canonical `CLAUDE.base.md` conventions and the
  Builder-pattern scaffold (Product / Builder / Director / Client).
