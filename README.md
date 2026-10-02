# Synthetic Data Playground

A deterministic commerce lab: generate events, validate their lifecycle, quarantine
bad records and inspect the SQL behind conversion, revenue and retention. Everything
is synthetic; the supported Python service needs no database or credentials.

[Explore the portfolio UI](https://jckail.com/dataplayground) ·
[Architecture](docs/architecture.mdx) ·
[API and operations](docs/service-operations.mdx) ·
[Design canvas](https://superdesign.dev/teams/daa6c1df-346f-4dc3-81dd-fb4f462aff90/projects/455b1495-879c-4308-8228-7c12040fa5a2)

## Quickstart

From the repository root, use Python 3.12 with venv support:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lab-dev.txt
.venv/bin/python -m playground simulate --seed 42 --days 7 --daily-signups 5
.venv/bin/python -m playground export --output artifacts/catalog.json
.venv/bin/uvicorn playground.api:app --host 127.0.0.1 --port 8010 --workers 1
```

The CLI works without a running service. The last command serves the optional API;
open `http://127.0.0.1:8010/docs`. The exported catalog includes four scenarios,
independent graph/vector exploration and executable architecture demonstrations.

## What to explore

| Topic | Guide |
| --- | --- |
| Pipeline, source ownership and result semantics | [Architecture](docs/architecture.mdx) |
| Requests, limits, local operation and failure handling | [API and operations](docs/service-operations.mdx) |
| Real DAG callbacks, retries and blocked dependencies | [Architecture workbench](docs/architecture-workbench.md) |
| Synthetic graph and handcrafted feature vectors | [Exploration](docs/exploration.md) |
| Detailed engine and portfolio adapter contract | [Implementation reference](docs/playground-architecture.md) |

The [portfolio repository](https://github.com/jckail/portfolio) owns the React UI.
This repository owns the headless service and reproducible catalog. Money is integer
cents; collected revenue is not MRR. Unobserved retention ages are `null`, not zero.
The same configuration, scenario and engine version reproduce the same result.

## Verify

```bash
.venv/bin/ruff check playground tests
.venv/bin/python -m unittest discover -s tests -v
```

CI also compares two catalog exports byte for byte. A separate pinned verification
job exercises actual legacy chart/router modules with inert database and HTTP
boundaries; see [verification details](docs/service-operations.mdx#verification).

## Legacy boundary

`app.main`, `streamlit_app/`, migrations, `requirements.txt` and the original
Compose files belong to the earlier PostgreSQL experiment. Its remaining database
and scheduler operations are not established as functional. Use
`playground.api:app`, `requirements-lab.txt` and `compose.lab.yml` for the supported
lab. Hosted deployment is not configured by this repository.
