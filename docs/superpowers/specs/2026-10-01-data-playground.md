# Data Playground portfolio lab

The visitor explores an end-to-end synthetic commerce pipeline: signup, shop activation, payment, and churn. They compare reproducible scenarios, inspect data-quality failures, and trace aggregate metrics to events and SQL. All data is clearly labeled synthetic. The existing PostgreSQL/Streamlit experiment stays available as a legacy implementation; the new supported lab has an independent, testable entrypoint.

## Ownership and delivery

`data_playground` owns the Python simulation, validation, SQL analytics, deterministic export, standalone bounded FastAPI service, tests, and documentation. The portfolio owns a lazy React page at `/dataplayground`, a validated read-only catalog API, and an optional same-origin adapter to the standalone service. The default experience ships generated, versioned artifacts and requires no database or external service. Custom simulation controls are enabled only when that service is configured. Do not duplicate the simulator in JavaScript. Existing portfolio work is preserved on its refresh branch; the integration is a separate branch based on it.

## Data contract (schema version 1)

A catalog contains `schema_version: 1`, `engine_version: "1.0.0"`, `source: {repository, command}`, and `runs: RunResult[]`. Each run has `id`, `scenario: {id,name,description}`, `config`, `summary`, `daily`, `funnel`, `cohorts`, `pipeline`, `quality`, `events`, `quarantined`, and `lineage`.

Config: `seed` (integer 0..2147483647), `days` (integer 7..90), `daily_signups` (integer 5..100), `activation_rate`, `payment_rate` (0..1), `churn_rate` (0..0.2 per day), `duplicate_rate`, `invalid_rate` (0..0.2). Default start date is fixed at 2025-01-01. Rates are finite numbers. Unknown input fields are rejected.

Summary: `signups`, `activated_users`, `paying_users`, `active_customers`, `revenue_cents` (nonnegative integers), `conversion_rate`, `churn_rate`, `quality_pass_rate` (fractions 0..1). Revenue is collected synthetic subscription payments, not MRR. Churn rate is cumulative churned customers divided by ever-paying customers, not the configured daily hazard.

Daily entries: `date`, `signups`, `activations`, `payments`, `churns`, `revenue_cents`, `active_customers`. Funnel: `{stage,users,rate}`. Cohorts: `{cohort,size,retention:(number|null)[]}`; null means observation unavailable, not zero retention. Events: `{event_id,occurred_at,user_id,event_type,amount_cents,channel,plan}`. Event types: `signup`, `activation`, `payment`, `churn`. Events shown are a bounded accepted sample (100); quarantined samples (50) have `{event_id,event_type,reason}`.

Pipeline: `{id,name,input_count,output_count,rejected_count,description}`. Quality: `{id,name,status:'pass'|'warn',checked,failed,description}`. Lineage: `{metric,definition,source,sql}`. Query text is educational and executed internally by the Python pipeline; the public API does not accept SQL.

## Processing and correctness

Use a local seeded RNG; run ids and results are repeatable for the same configuration. Inject duplicates and malformed records deliberately, deduplicate by event id, validate event fields and relationships, and quarantine rejected records with reasons. Aggregate validated events with SQLite in memory using standard-library SQL support. Decimal currency uses integer cents. Reconcile stage counts, funnel totals, daily revenue, and customer balance. Export four scenarios: baseline, acquisition, retention, quality. Production data and credentials are never needed by tests.

## API and user interface

Standalone endpoints: GET `/health`, GET `/api/catalog`, POST `/api/simulate` with Config, returning RunResult. Bound request sizes, concurrency, and execution cost. Portfolio GET `/api/dataplayground` returns catalog plus `live_simulation: bool`; POST `/api/dataplayground/simulate` uses the configured fixed service URL, bounded timeout and validated input/output. No configured upstream means HTTP 503, with the UI explaining how to run locally. No silent switch from a failed live run to a preset.

The page uses existing typography and theme tokens, a wide pipeline visualization, scenario selection, revenue chart, conversion funnel, cohort grid, quality report, searchable event sample, and expandable SQL lineage. An explanatory project intro and source/reproduction links make the engineering work legible. Native buttons, keyboard navigation, accessible table alternatives, loading/error/empty states, mobile layout, both themes, and reduced motion are required. The homepage must not eagerly load the lab.

## Acceptance

Python unit tests verify repeatability, bounds, reconciliation, corruption isolation, cohort censoring, export parity, and service validation. Portfolio tests verify catalog validation, unavailable/failed upstream behavior, and public route deep links. Frontend tests exercise scenario switching, event filtering, and error recovery. Run full appropriate lint/type/test/build checks and browser interactions at desktop and mobile sizes. Production deployment follows existing CI, never a laptop deploy script.
