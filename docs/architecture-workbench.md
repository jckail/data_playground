# Executable architecture workbench

The optional `catalog.architecture` object adds dependency DAGs with executed run
traces, source-backed models and engineering decisions. Schema version 1 and engine
version 1.0.0 remain unchanged. Older catalogs need not include this extension.

Replay actual callbacks without a service or external database:

```bash
.venv/bin/python -m playground orchestrate --failure none
.venv/bin/python -m playground orchestrate --failure analytics-transient
.venv/bin/python -m playground orchestrate --failure validation-permanent
```

The CLI prints JSON without writing files unless `--output` is explicitly supplied.
The scheduler itself performs no file, cloud or network writes. Its default
configuration is seven days, five signups per day and seed 42. Each run executes
`generate_events`, `validate_events`, SQLite `aggregate`, `build_exploration`,
aggregate reconciliation and canonical in-memory publication hashing. It validates
unknown dependencies, duplicate task IDs and cycles before running callbacks.
Available tasks run in stable declaration order subject to dependencies.

The normal run succeeds. The transient example injects an availability fault
before the first analytics aggregation, then executes aggregation on attempt two.
Only `RetryableTaskError` triggers another attempt, up to the task's declared
limit. Both runs publish the same canonical SHA-256 payload fingerprint.
The permanent example executes record validation, then injects a task contract
failure: analytics, reconciliation and publication are blocked with attempt zero.
The independent exploration branch still executes. The trace records callback
attempts and dependency blocking, with no invented durations or timestamps.
These failures are explicit demonstrations, not observed infrastructure incidents.

Record quarantine is separate: normal record defects are rejected and counted by
`validate_events`, while the validation task can still succeed. Scheduler failure
represents an inability to complete the task or satisfy its publication contract.
No failed publication receives a fingerprint.

The model browser describes actual SQLite `events` and temporary `customers`
tables. SQLite enforces the event primary key; Python enforces lifecycle ordering,
non-null values and enum/payment contracts before loading. There are no declared
SQLite foreign keys. Customer user IDs are unique by grouping, without a declared
primary-key constraint. Daily and cohort outputs are **query-result artifacts**,
not created SQL views; Python fills missing daily dates, appends active balances
and computes nullable retention ages. Commerce records and graph/vector outputs
are independent JSON artifacts, not dbt models or database tables. The vector
model is a logical projection of the product fields, not an additional vector
index. SQL is present only where the engine really executes SQL.

Decision records distinguish the running demonstration from proposed production
storage partitions, durable replay keys, publication pointers, observability and
cost controls. Deterministic local replay does not implement distributed
exactly-once processing. No orchestrator, warehouse, graph store, vector database
or cloud provider is required for this demonstration.

Run `.venv/bin/python -m unittest discover -s tests -v` and
`.venv/bin/ruff check playground tests` for executable scheduler, failure,
source-schema, replay and export validation.
