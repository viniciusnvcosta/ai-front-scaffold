# Changelog

All notable changes to **`ai-front-scaffold`** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Generated repos pin a scaffold tag in `.copier-answers.yml` and adopt changes
deliberately with `just update` (`copier update`), reviewing the diff before
merging. A **MINOR** bump means new "from base" capabilities flow into child
repos on their next update; read the entry before running it.

## [Unreleased]

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
