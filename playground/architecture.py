"""Executable local DAG and source-backed architecture metadata; no external I/O."""
import hashlib
import json
from collections import Counter

from .analytics import COHORT_SQL, CUSTOMERS_SQL, DAILY_SQL, aggregate
from .config import SimulationConfig
from .exploration import build_exploration
from .pipeline import validate_events
from .simulation import generate_events


class RetryableTaskError(RuntimeError):
    """An explicitly transient task failure, distinct from quarantined records."""


def topological_order(tasks):
    """Stable declaration-order traversal; reject invalid graphs before callbacks."""
    ids = [task['id'] for task in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate task ID')
    for task in tasks:
        if any(dep not in ids for dep in task['depends_on']):
            raise ValueError('unknown task dependency')
        if type(task['max_attempts']) is not int or task['max_attempts'] < 1:
            raise ValueError('max_attempts must be a positive integer')
    pending = list(tasks)
    order = []
    done = set()
    while pending:
        ready = next((task for task in pending if set(task['depends_on']) <= done), None)
        if ready is None:
            raise ValueError('dependency cycle')
        pending.remove(ready)
        order.append(ready)
        done.add(ready['id'])
    return order


def execute_dag(tasks, callbacks):
    """Execute each ready callback; retry only explicitly transient exceptions."""
    order = topological_order(tasks)
    if set(callbacks) != {task['id'] for task in tasks}:
        raise ValueError('callbacks must exactly match tasks')
    outputs, statuses, trace = {}, {}, []
    for task in order:
        key = task['id']
        blocked = [dep for dep in task['depends_on'] if statuses[dep] != 'success']
        if blocked:
            statuses[key] = 'blocked'
            trace.append(dict(task_id=key, attempt=0, status='blocked', detail='Unmet dependencies: ' + ', '.join(blocked)))
            continue
        for attempt in range(1, task['max_attempts'] + 1):
            try:
                output, detail = callbacks[key](outputs, attempt)
            except Exception as exc:
                statuses[key] = 'failed'
                trace.append(dict(task_id=key, attempt=attempt, status='failed', detail=str(exc)))
                if isinstance(exc, RetryableTaskError) and attempt < task['max_attempts']:
                    continue
                break
            outputs[key] = output
            statuses[key] = 'success'
            trace.append(dict(task_id=key, attempt=attempt, status='success', detail=detail))
            break
    return outputs, trace


def task_metadata():
    rows = (
        ('generate', 'Generate events', [], 'Seeded lifecycle source records.', 'playground.simulation.generate_events', 'Raw event list', 1),
        ('validate', 'Validate lifecycle', ['generate'], 'Deduplicate, validate and quarantine record defects.', 'playground.pipeline.validate_events', 'Accepted events, quarantine sample and quality counts', 1),
        ('analytics', 'Aggregate in SQLite', ['validate'], 'Load accepted events and execute SQL in ephemeral SQLite.', 'playground.analytics.aggregate', 'Summary, daily, funnel, cohorts and SQL lineage', 2),
        ('exploration', 'Build commerce features', [], 'Independent seeded graph and product feature vectors.', 'playground.exploration.build_exploration', 'Products, shoppers, purchases, graph and vectors', 1),
        ('reconcile', 'Reconcile contracts', ['analytics', 'exploration'], 'Check lifecycle revenue and commerce graph quantities before publishing.', 'playground.architecture.reconcile', 'Validated in-memory publication payload', 1),
        ('publish', 'Publish in memory', ['reconcile'], 'Canonical JSON hash; no files, cloud calls or production writes.', 'playground.architecture.fingerprint_payload', 'SHA-256 content fingerprint', 1),
    )
    return [dict(id=key, name=name, depends_on=deps, description=description, source=source, output=output,
                 max_attempts=attempts, idempotency='Same seed, configuration, source and engine version produce the same output; no external side effects.')
            for key, name, deps, description, source, output, attempts in rows]


def fingerprint_payload(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def reconcile(analytics, exploration):
    summary, daily, funnel, cohorts, lineage = analytics
    if summary['revenue_cents'] != sum(row['revenue_cents'] for row in daily):
        raise ValueError('lifecycle revenue reconciliation failed')
    quantities = Counter()
    for row in exploration['purchases']:
        quantities[row['customer_id'], row['product_id']] += row['quantity']
    edges = {(row['source'], row['target']): row['weight'] for row in exploration['graph']['edges'] if row['relation'] == 'purchased'}
    if dict(quantities) != edges:
        raise ValueError('commerce graph reconciliation failed')
    return dict(summary=summary, daily=daily, funnel=funnel, cohorts=cohorts, lineage=lineage, exploration=exploration)


def demonstration_run(mode, tasks):
    config = SimulationConfig(days=7, daily_signups=5)

    def generate(outputs, attempt):
        raw = generate_events(config)
        return raw, f'Generated {len(raw)} raw events with seed {config.seed}.'

    def validate(outputs, attempt):
        result = validate_events(outputs['generate'], config)
        if mode == 'validation-failure':
            # The validator really ran; this explicit task-level contract fault is
            # separate from ordinary malformed rows handled by quarantine.
            raise ValueError('Injected permanent validation task contract failure after record validation; no retry.')
        return result, f'Accepted {len(result[0])} events; rejected records remain quarantine, not task retries.'

    def analytics(outputs, attempt):
        if mode == 'analytics-retry' and attempt == 1:
            raise RetryableTaskError('Injected transient analytics availability fault before aggregation; retry is safe.')
        result = aggregate(outputs['validate'][0], config, len(outputs['generate']))
        return result, 'Executed SQLite aggregation from accepted events.'

    def exploration(outputs, attempt):
        result = build_exploration()
        return result, 'Built independent 48-product, 32-shopper commerce branch.'

    def contracts(outputs, attempt):
        result = reconcile(outputs['analytics'], outputs['exploration'])
        return result, 'Lifecycle revenue and purchase-edge quantities reconcile.'

    def publish(outputs, attempt):
        result = fingerprint_payload(outputs['reconcile'])
        return result, 'Canonical payload published in memory; SHA-256 ' + result

    callbacks = dict(generate=generate, validate=validate, analytics=analytics, exploration=exploration, reconcile=contracts, publish=publish)
    outputs, trace = execute_dag(tasks, callbacks)
    names = {'normal': 'Normal execution', 'analytics-retry': 'Transient analytics retry', 'validation-failure': 'Permanent validation failure'}
    descriptions = {'normal': 'All six callbacks execute successfully in deterministic dependency order.',
                    'analytics-retry': 'Only an explicitly transient task fault retries. Final publication equals the normal run.',
                    'validation-failure': 'Permanent task failure blocks dependent tasks while independent commerce exploration still executes.'}
    return dict(id=mode, name=names[mode], description=descriptions[mode], trace=trace,
                published='publish' in outputs, fingerprint=outputs.get('publish'))


def column(name, kind, description, nullable=False, key='none'):
    return dict(name=name, type=kind, nullable=nullable, key=key, description=description)


def model_metadata():
    def model(key, name, kind, description, grain, materialization, source, columns, deps, sql, contracts):
        return dict(id=key, name=name, kind=kind, description=description, grain=grain, materialization=materialization,
                    source=source, columns=columns, depends_on=deps, sql=sql, contracts=contracts)
    event_columns = [column('event_id', 'TEXT', 'Unique accepted event identifier.', key='primary'),
                     column('occurred_at', 'TEXT', 'Validated UTC timestamp within the observation window.'),
                     column('user_id', 'TEXT', 'Lifecycle user identifier; signup precedes downstream events.'),
                     column('event_type', 'TEXT', 'signup, activation, payment or churn.'),
                     column('amount_cents', 'INTEGER', 'Bounded integer cents; payment amounts match plan.'),
                     column('channel', 'TEXT', 'Validated acquisition channel.'), column('plan', 'TEXT', 'Validated subscription plan.')]
    return [
        model('events', 'Accepted lifecycle events', 'table', 'Actual in-memory SQLite table; only event_id PRIMARY KEY is enforced by SQLite. Other contracts run in Python before loading.', 'One accepted event', 'Ephemeral SQLite table and user_events(user_id,event_type) index', 'playground.analytics.aggregate / playground.pipeline.validate_events', event_columns, [],
              'CREATE TABLE events(event_id TEXT PRIMARY KEY, occurred_at TEXT, user_id TEXT, event_type TEXT, amount_cents INTEGER, channel TEXT, plan TEXT)', ['Unique non-null event IDs after validation', 'Valid enums and non-null fields checked in Python', 'Signup, activation, payment and churn order checked in Python']),
        model('customers', 'Derived lifecycle customers', 'table', 'Actual CREATE TEMP TABLE AS result; grouped user_id is unique by derivation, not a declared SQLite primary key.', 'One lifecycle user including non-paying users', 'Ephemeral SQLite temporary table; customer_cohort(first_payment) index', 'playground.analytics.CUSTOMERS_SQL', [column('user_id', 'TEXT', 'Grouping key from accepted events.', key='foreign'), column('first_payment', 'TEXT', 'UTC first-payment date; null for non-payers.', True), column('churn_date', 'TEXT', 'UTC churn date; null when no churn.', True)], ['events'], CUSTOMERS_SQL, ['Every user originates in accepted events', 'Non-payers have nullable first_payment']),
        model('daily', 'Daily lifecycle metrics', 'artifact', 'Exported SELECT results filled across the observation window, with active-customer balance appended in Python; no SQL view is created.', 'One UTC observation day', 'JSON query-result artifact', 'playground.analytics.DAILY_SQL / BALANCE_SQL / aggregate', [column('date', 'TEXT', 'Observation day.', key='primary')] + [column(key, 'INTEGER', 'Daily count or collected cents.') for key in ('signups', 'activations', 'payments', 'churns', 'revenue_cents', 'active_customers')], ['events'], DAILY_SQL, ['One row per configured day', 'Daily collected cents sum to summary revenue']),
        model('cohorts', 'Payment cohort retention', 'artifact', 'Exported cohort SQL results with censored weekly retention computed by parameterized queries; no SQL view is created.', 'One first-payment date cohort', 'JSON query-result artifact', 'playground.analytics.COHORT_SQL / RETENTION_SQL / aggregate', [column('cohort', 'TEXT', 'First-payment UTC date.', key='primary'), column('size', 'INTEGER', 'Ever-paying users in cohort.'), column('retention', 'ARRAY[NUMBER|null]', '13 weekly fractions; future observations are null.')], ['customers'], COHORT_SQL, ['Cohort sizes sum to ever-paying users', 'Unobserved ages are null, not zero']),
        model('products', 'Synthetic products', 'artifact', 'Invented products independent of lifecycle scenarios; no commerce SQL tables are created.', 'One product', 'Seeded in-memory records exported as JSON', 'playground.exploration.PRODUCTS / build_exploration', [column('id', 'STRING', 'Stable product ID.', key='primary'), column('name', 'STRING', 'Invented product name.'), column('category', 'STRING', 'One of six category labels.'), column('description', 'STRING', 'Transparent feature input description.'), column('price_cents', 'INTEGER', 'Positive invented price in integer cents.'), column('vector', 'ARRAY[NUMBER]', 'Eight nonnegative unit-normalized handcrafted features.')], [], '', ['48 unique product IDs', 'Positive integer cents', 'Exactly eight finite nonnegative unit-vector coordinates']),
        model('shoppers', 'Synthetic commerce shoppers', 'artifact', 'Commerce identities are not joined to lifecycle users.', 'One synthetic shopper', 'Seeded in-memory records exported as JSON', 'playground.exploration.build_exploration', [column('id', 'STRING', 'Stable shopper ID.', key='primary'), column('name', 'STRING', 'Synthetic display name.'), column('segment', 'STRING', 'Primary category interest.')], [], '', ['32 unique shopper IDs', 'Independent identity domain from lifecycle users']),
        model('purchases', 'Synthetic purchase rows', 'artifact', 'Five seeded rows per shopper, including a deliberate repeated product; no timestamps or lifecycle revenue reconciliation.', 'One purchase row', 'Seeded in-memory records exported as JSON', 'playground.exploration.build_exploration', [column('id', 'STRING', 'Unique purchase row ID.', key='primary'), column('customer_id', 'STRING', 'References shoppers.id.', key='foreign'), column('product_id', 'STRING', 'References products.id.', key='foreign'), column('quantity', 'INTEGER', 'Purchased units, from 1 to 3.')], ['products', 'shoppers'], '', ['160 unique purchase IDs', 'References resolve to shoppers and products', 'Positive integer quantities']),
        model('graph', 'Commerce relationship graph', 'artifact', '86 typed nodes plus weighted directed relationships derived from purchases and categories.', 'One graph envelope; node ID and (source,target,relation) identify nested records', 'JSON graph artifact; no graph database', 'playground.exploration.build_exploration', [column('nodes', 'ARRAY[OBJECT]', 'Unique customer/product/category nodes.'), column('edges', 'ARRAY[OBJECT]', 'purchased sums quantity; belongs_to has weight 1.')], ['products', 'shoppers', 'purchases'], '', ['All edge endpoints exist', 'Purchase edges reconcile to summed units, not transaction count', 'Every product has exactly one category edge']),
        model('vectors', 'Product feature vectors', 'artifact', 'Logical projection of products.vector with shared dimension names, not a second stored vector index or learned embedding.', 'One eight-coordinate vector per product', 'Nested JSON feature projection; no vector database', 'playground.exploration.DIMENSIONS / PRODUCTS / build_exploration', [column('product_id', 'STRING', 'Projection of products.id.', key='foreign'), column('dimensions', 'ARRAY[STRING]', 'Ordered category, portability and premium dimension labels.'), column('vector', 'ARRAY[NUMBER]', 'Projection of products.vector.')], ['products'], '', ['Eight named dimensions', 'Finite nonnegative unit vectors', 'Cosine equals dot product within floating-point tolerance']),
    ]


def decision_metadata():
    rows = (
        ('partitioning', 'Partitioning and storage', 'Demo uses small ephemeral SQLite tables and no partitions.', 'Simple reproducibility; full scans and per-day queries become expensive at scale.', 'aggregate opens :memory: and creates user_events and customer_cohort indexes.', 'Proposal: durable event storage partitioned by UTC date, with bounded late-arrival windows and measured query plans.'),
        ('replay', 'Replay and idempotence', 'Demo regenerates from seed/config and hashes canonical in-memory output.', 'Repeatability holds for the same code/version; no durable exactly-once guarantees.', 'Normal and transient-retry runs publish the same SHA-256; failed runs do not publish.', 'Proposal: content-addressed versioned artifacts, durable task keys and atomic publish pointers; external side effects need deduplication.'),
        ('contracts', 'Contracts and dependencies', 'Validate records, reconcile aggregates, and block descendants of failed tasks.', 'Record quarantine handles bad rows; task retry handles only explicitly transient execution faults.', 'validate_events runs record checks; the scheduler retries RetryableTaskError and records blocked descendants.', 'Proposal: versioned schemas, migration compatibility, referential tests and publish gates in an orchestrator.'),
        ('observability', 'Observability', 'Deterministic attempt/status traces and record-quality counts expose local execution.', 'No timings, distributed logs, alerting or persistent run history are implemented.', 'All trace entries come from executed callbacks or dependency blocking; no fabricated elapsed times.', 'Proposal: durable run IDs, structured logs, latency metrics, lineage, freshness SLOs and failure alerts.'),
        ('cost-scale', 'Cost and scale', 'Demo runs bounded synthetic records locally with SQLite and transparent vectors.', 'No provider bills; graph and vector inspection scans tiny arrays and does not benchmark production workloads.', 'Architecture runs use seven days and five daily signups; commerce contains 48 products and 160 purchases.', 'Proposal: profile representative loads before adopting columnar analytics, graph storage or a vector index; budget compute and retention explicitly.'),
    )
    return [dict(id=key, title=title, choice=choice, tradeoff=tradeoff, evidence=evidence, production_path=production)
            for key, title, choice, tradeoff, evidence, production in rows]


def build_architecture():
    tasks = task_metadata()
    return dict(dags=[dict(id='lifecycle-exploration', name='Lifecycle and commerce publication',
                           description='Executable local dependency scheduler with independent branches, bounded transient retry and contract-gated in-memory publication. Injected faults are demonstrations, not production incidents.',
                           tasks=tasks, runs=[demonstration_run(mode, tasks) for mode in ('normal', 'analytics-retry', 'validation-failure')])],
                models=model_metadata(), decisions=decision_metadata())
