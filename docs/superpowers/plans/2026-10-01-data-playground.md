# Data Playground implementation plan

**Goal:** Deliver a reproducible data-engineering lab and its portfolio frontend.
**Architecture:** Python owns generation, validation, SQL analytics, API, and versioned demo artifacts. Portfolio consumes the artifact through typed API routes; custom runs use an optional bounded upstream. UI is a lazy isolated page.
**Tech stack:** Python standard library, existing FastAPI/Pydantic, React/TypeScript, existing test tools. No new portfolio runtime dependency.
**Spec:** ../specs/2026-10-01-data-playground.md

## Execution units

1. Engine: create `playground/config.py`, `simulation.py`, `pipeline.py`, `analytics.py`, `catalog.py`, `__main__.py`, and `tests/test_pipeline.py`. Export `SimulationConfig`, `run_simulation(config, scenario=None) -> dict`, and `build_catalog() -> dict`. Validate seeds and rates; derive deterministic event ids and preserve integer money. Tests compare equal runs, reconcile revenue against events/SQL, confirm quarantine, exercise empty conversions and censored cohorts. Run `python -m unittest discover -s tests`.
2. Supported service: create `playground/api.py`, `requirements-lab.txt`, `requirements-lab-dev.txt`, `Dockerfile.lab`, `compose.lab.yml`, and `.github/workflows/lab.yml`. Consume the engine interfaces and implement validated read-only catalog plus bounded custom simulations. API tests use dummy inputs, never legacy database scripts. Document independent startup and explicit legacy status in README.
3. Portfolio adapter: add Pydantic contract, cached generated catalog loader, thin API routes, optional upstream configuration, and tests. Copy only the deterministic catalog artifact with source metadata. Expose GET `/api/dataplayground` and POST `/api/dataplayground/simulate` using existing HTTP dependencies. Test missing service, invalid input, upstream failure, and contract errors.
4. Frontend: add `frontend/src/app/dataplayground/` components, styles, and behavior tests; lazy route from actual entrypoint; add endpoint constants and existing project demo link. Render pipeline, scenario comparisons, metrics, retention, quality, event filtering, and SQL. Use existing theme tokens, no chart dependency. Run lint/type-check/test/build and browser checks.
5. Integration: generate catalog with `python -m playground export`, compare repeated hashes, run both repository suites, review changes, refresh shared Graphify, commit and push isolated branches, open reviewable PRs. Keep production deployment separate from feature-branch publication.

## Decisions

The user selected end-to-end data engineering. The new lab is isolated from the old PostgreSQL experiment so visitors can use it without a database and legacy schema changes cannot corrupt the demonstration. The portfolio integration builds on the existing refresh branch without modifying its worktree. A default catalog supports the full inspection flow even before a simulation service is hosted.
