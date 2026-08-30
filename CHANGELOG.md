# Changelog

All notable changes to **`ai-front-scaffold`** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Generated repos pin a scaffold tag in `.copier-answers.yml` and adopt changes
deliberately with `just update` (`copier update`), reviewing the diff before
merging. A **MINOR** bump means new "from base" capabilities flow into child
repos on their next update; read the entry before running it.

## [Unreleased]

## [0.5.0]

Credential redaction in logs, and an image that actually installs the project —
"from base", reaches every front on `copier update`. Both halves come from
defects found in **production** in fronts generated from this template, not from
a hardening checklist.

### Added
- **`observability/redact.py` + wiring in `main.py`.** Every front now installs a
  redacting log `Formatter` at import time (patterns only, covering whatever logs
  before config exists — including front construction, which can already make
  requests), and reinstalls it in `main()` with `LOG_LEVEL` honoured and the
  front's own sensitive values registered via `register_secrets([...])`.
  Why a `Formatter` and not a `Filter`: the leak arrives through `record.args`
  and through the traceback, and a `record.msg` filter sees neither. Why
  value-registration on top of patterns: pattern matching cannot catch a secret
  logged bare, without a URL around it (a config dict, for instance).
  The originating incident is documented in the module header and in
  `CLAUDE.base.md` §4 invariant 5 — on 06/08/2026 a generated front published
  its system-of-record **write credential** once per request, because the HTTP
  client logs the full URL at INFO and the credential travelled inside it.
  `register_secrets([])` ships as an explicit empty call in `main()`, so adopting
  fronts see the seam they are expected to fill.
- **`just cold-install`.** Proves the RUNTIME image imports the app with
  production dependencies only: `uv sync --frozen --no-dev` into a throwaway venv,
  then `pkgutil.walk_packages` over the whole package. It walks every module, not
  just `main`, because in the Builder pattern the imports happen inside the
  `with_*` steps — importing the entry module does not exercise the real chain.
  Now part of `just check` (see Changed).
- **17 tests** covering redaction (`tests/unit/test_log_redaction.py`) plus the
  `APP_ROLE` addition in `test_app_role.py`.
- **§4 invariant 5 of `CLAUDE.base.md` extended to logs**, with two new items on
  the front checklist: `main.py` must install `install_log_redaction()` and pass
  every sensitive config value to `register_secrets()` — verified **in the
  artifact**, not only in tests — and `just cold-install` must pass.

### Changed
- **`just check` is now `lint test contracts cold-install`.** The recipe arrived
  in 0.4.0 with three steps; `cold-install` is the only one of the four that
  answers "does the image come up?" — `test` runs in the DEV venv and cannot see
  a runtime dependency misclassified under `dev`.
- **`Dockerfile` now runs two `uv sync` and sets `UV_NO_SYNC=1`.** ⚠️ **Practical
  break for adopters — see Migration.** The previous template had a single sync
  *before* `COPY . .`, so it installed the dependencies and **never the project**;
  `CMD ["uv", "run", ...]` hid this by syncing at runtime, on every container
  boot. Found in production in three fronts (`whatsapp-sales-agent`,
  `campaign-manager`, `bitrix-orchestrator`). The consequences were all real: the
  container only started if PyPI was reachable; `uv run` synced the DEFAULT group,
  so the "production" image installed ruff and pytest at every boot; the artifact
  stopped being reproducible, which voids the point of pinning an image by digest
  in IaC; and in one front the defect stayed invisible until `--no-dev` was fixed,
  then surfaced as a **60-second crash-loop in production** because a runtime
  dependency was classified under `dev` and the boot-time sync had been installing
  it by accident.
  First sync installs dependencies only (`--no-install-project`) so the layer
  stays cached when just the code changes; the second, after `COPY . .`, installs
  the project. `UV_NO_SYNC=1` then stops `uv run` from re-syncing on every
  invocation — including in the `HEALTHCHECK`, which runs every 30s.
- **`logging.basicConfig(level=logging.INFO)` removed from `main.py`**, replaced
  by `install_log_redaction()`. Not a style preference: it is the raw
  `basicConfig` that let the incident above happen.

### Fixed
- **`redact()` no longer crashes on a group-less extra pattern.** Substitution
  always used `\1`, so a front adding a pattern to `EXTRA_PATTERNS` without a
  capture group — an easy mistake — raised `re.error` and could break the logging
  path at runtime. Patterns with no group now replace the whole match.
- **`LOG_LEVEL` is now honoured case-insensitively and never aborts the boot.**
  The level string went straight to `logging.basicConfig`/`setLevel`, which raise
  `ValueError` on anything but the canonical uppercase name — so `LOG_LEVEL=debug`
  killed the process. Since the call happens in `main()` *after* `build()`, it
  took down an already-assembled front: crash-loop. Values are now normalised
  (case, surrounding space, numeric strings) and an unknown name degrades to INFO
  with a warning. A wrong log level is never a reason for the service not to come
  up. Note this is a live behaviour change relative to 0.4.0, where
  `logging.basicConfig(level=logging.INFO)` ignored `LOG_LEVEL` entirely — fronts
  that set it will now actually get that level.
- **`just --list` is readable again.** `just` uses only the last contiguous
  comment line above a recipe as its doc, so the rationale blocks on `test`,
  `cold-install` and `check` rendered as mid-sentence fragments — in the recipe
  that is every generated front's `default`.

### Migration
- **Rebuild the image after `just update`.** The new `Dockerfile` produces a
  different layer set and therefore a **new digest**; any IaC pinning the old
  digest must be updated. This is the one item in this release that needs human
  action beyond reviewing the `copier update` diff.
- **Register your secrets.** `register_secrets([])` lands empty. Every front
  should pass its own sensitive config values — a webhook URL with an embedded
  credential, a token, a password. Patterns alone will not cover a secret logged
  bare.
- Fronts adopting this release inherit `cold-install` inside `just check`, which
  can turn a previously green gate red if the image never installed the project.
  That failure is the feature.

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

### Fixed
- **Generated-project skeleton made lint-clean, and `ruff` pinned to stay that
  way.** This release is what turns `just lint` into a blocking CI gate (via
  `just check`, run by the new `azure-pipelines.yml` Gate stage), so the
  scaffold's own pre-existing rule drift — `ruff>=0.6` had quietly resolved to
  0.16.0, whose newer default ruleset flagged 25 findings across
  `ops/healthcheck.py`, `front/builder.py`, `front/product.py`,
  `observability/__init__.py`, and `tests/unit/test_healthcheck_modes.py` —
  would otherwise have shipped as a day-one failure on every new front. Fixed
  in the skeleton, not suppressed:
  - `front/builder.py.jinja` / `observability/__init__.py`: 19×`UP037`
    (unneeded quoted forward refs now that `from __future__ import
    annotations` is in effect) — quotes dropped.
  - `ops/healthcheck.py.jinja`: the import guard now catches `ImportError`
    specifically (that's the one real failure mode of "module name is
    templated; if import path differs, treat as unhealthy" — no longer a
    blind `except Exception`); the now-unnecessary `# noqa: F401` on that
    import is gone (`build` is used lower down, so nothing was ever
    unused — `RUF100`); the outer `except Exception` in `main()` is a
    deliberate last-resort process boundary (this script's entire contract is
    "any failure ⇒ unhealthy"), kept broad but now paired with
    `log.exception(...)` — ruff's own documented exemption for blind excepts
    that log with `exc_info` — instead of silently swallowing the traceback.
  - `front/product.py`: `readiness()`'s per-resource probe catch mirrors the
    same, already-established pattern one function below it in this file
    (`shutdown()`'s resource-close loop) — `log.exception(...)` instead of
    `log.warning(...)`, satisfying the identical ruff exemption instead of
    guessing at a narrower exception type for an arbitrary duck-typed
    `ready()`/`ping()` probe.
  - `tests/unit/test_healthcheck_modes.py.jinja`: both `subprocess.run(...)`
    calls gain explicit `check=False` (`PLW1510`) — correct as-is, since the
    return code itself is the assertion, not an error signal.
  - `pyproject.toml.jinja`: `ruff` pin narrowed to `>=0.16,<0.17` (the minor
    verified clean above) so the ruleset can't silently drift again on a
    future `uv sync`.

### Notes
- Recipe construction order is unchanged; no builder steps or public
  signatures were altered.
- `just check` (lint + coverage-gated test + contracts) is green on all eight
  freshly generated recipes, including `scheduler` (the thinnest assembly
  order) — verified by generating each from this tag and running `just
  check` end to end (see report for full transcripts).

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
