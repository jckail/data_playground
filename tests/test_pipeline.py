"""Business invariants, quality isolation, and deterministic artifact contract."""
import json
import os
import stat
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from playground.catalog import build_catalog, write_json_atomic
from playground.config import SimulationConfig
from playground.pipeline import run_simulation, validate_events
from playground.simulation import generate_events


class PipelineTests(unittest.TestCase):
    def test_repeatable_identity_covers_configuration_scenario_and_version(self):
        config = SimulationConfig(days=7, daily_signups=5)
        run = run_simulation(config)
        self.assertEqual(run, run_simulation(config.to_dict()))
        self.assertNotEqual(run['id'], run_simulation(SimulationConfig(days=8, daily_signups=5))['id'])
        self.assertNotEqual(run['id'], run_simulation(config, dict(id='other', name='Other', description='Other'))['id'])
        with patch('playground.pipeline.ENGINE_VERSION', '2.0.0'):
            self.assertNotEqual(run['id'], run_simulation(config)['id'])

    def test_bounds_types_unknown_fields_and_nonfinite(self):
        bad = [('seed', -1), ('seed', 2147483648), ('seed', True), ('days', 6), ('days', 91),
               ('daily_signups', 4), ('daily_signups', 101), ('days', 7.0), ('seed', '42')]
        for name in ('activation_rate', 'payment_rate', 'churn_rate', 'duplicate_rate', 'invalid_rate'):
            bad.extend((name, value) for value in (-.1, 1.1, float('nan'), float('inf'), 10 ** 400, True, '0.1', None))
        for name in ('churn_rate', 'duplicate_rate', 'invalid_rate'):
            bad.append((name, .21))
        for name, value in bad:
            with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                SimulationConfig(**{name: value})
        with self.assertRaises(TypeError):
            run_simulation({'unknown': 1})
        for scenario in ({}, dict(id='../bad', name='A', description='B'), dict(id='ok', name='', description='B')):
            with self.assertRaises(ValueError):
                run_simulation(SimulationConfig(), scenario)

    def test_reconcile_all_events_sql_summaries_daily_and_quality(self):
        config = SimulationConfig(days=45, duplicate_rate=.2, invalid_rate=.2)
        raw = generate_events(config)
        accepted, _, stages, checks = validate_events(raw, config)
        run = run_simulation(config)
        summary = run['summary']
        def users(kind):
            return {e['user_id'] for e in accepted if e['event_type'] == kind}
        self.assertEqual(summary['signups'], config.days * config.daily_signups)
        self.assertEqual(summary['activated_users'], len(users('activation')))
        self.assertEqual(summary['paying_users'], len(users('payment')))
        self.assertEqual(summary['active_customers'], len(users('payment') - users('churn')))
        self.assertEqual(summary['revenue_cents'], sum(e['amount_cents'] for e in accepted))
        self.assertEqual(summary['revenue_cents'], sum(d['revenue_cents'] for d in run['daily']))
        self.assertEqual(summary['quality_pass_rate'], len(accepted) / len(raw))
        self.assertEqual(summary['churn_rate'], len(users('churn')) / len(users('payment')))
        self.assertEqual(run['daily'][-1]['active_customers'], summary['active_customers'])
        self.assertEqual(sum(c['size'] for c in run['cohorts']), summary['paying_users'])
        self.assertEqual([f['users'] for f in run['funnel']], [summary[k] for k in ('signups', 'activated_users', 'paying_users')])
        for previous, current in zip(stages, stages[1:]):
            self.assertEqual(previous['output_count'], current['input_count'])
        self.assertEqual(len(raw) - len(accepted), sum(c['failed'] for c in checks))
        for stage in stages:
            self.assertEqual(stage['input_count'], stage['output_count'] + stage['rejected_count'])
        self.assertLessEqual(len(run['events']), 100)
        self.assertLessEqual(len(run['quarantined']), 50)
        self.assertTrue(all(type(e['amount_cents']) is int for e in accepted))
        for day in run['daily']:
            active = {e['user_id'] for e in accepted if e['event_type'] == 'payment' and e['occurred_at'][:10] <= day['date']}
            churned = {e['user_id'] for e in accepted if e['event_type'] == 'churn' and e['occurred_at'][:10] <= day['date']}
            self.assertEqual(day['active_customers'], len(active - churned))

    def test_published_lineage_queries_execute_and_match_results(self):
        config = SimulationConfig(days=7, daily_signups=5)
        events, _, _, _ = validate_events(generate_events(config), config)
        run = run_simulation(config)
        with sqlite3.connect(":memory:") as db:
            db.row_factory = sqlite3.Row
            db.execute("CREATE TABLE events(event_id TEXT, occurred_at TEXT, user_id TEXT, event_type TEXT, amount_cents INTEGER, channel TEXT, plan TEXT)")
            db.executemany("INSERT INTO events VALUES (:event_id,:occurred_at,:user_id,:event_type,:amount_cents,:channel,:plan)", events)
            queries = {row['metric']: row['sql'] for row in run['lineage']}
            totals = dict(db.execute(queries['Summary']).fetchone())
            for key in ('signups', 'activated_users', 'paying_users', 'revenue_cents'):
                self.assertEqual(totals[key], run['summary'][key])
            daily = [dict(row) for row in db.execute(queries['Daily activity'])]
            self.assertEqual(daily, [{k: v for k, v in row.items() if k != 'active_customers'} for row in run['daily']])
            self.assertEqual(db.execute(queries['Active customers'], ('2025-01-07', '2025-01-07')).fetchone()[0], run['summary']['active_customers'])
            db.execute(queries['Customer lifecycle'])
            cohorts = [dict(row) for row in db.execute(queries['Cohort size'])]
            self.assertEqual(cohorts, [{k: v for k, v in row.items() if k != 'retention'} for row in run['cohorts']])
            for row in cohorts:
                self.assertEqual(db.execute(queries['Cohort retention'], (row['cohort'], row['cohort'])).fetchone()[0], row['size'])
        self.assertEqual({e['event_type'] for e in run_simulation(SimulationConfig())['events']}, {'signup', 'activation', 'payment', 'churn'})

    def test_corruptions_do_not_change_business_outcomes(self):
        clean = run_simulation(SimulationConfig(duplicate_rate=0, invalid_rate=0))
        dirty = run_simulation(SimulationConfig(duplicate_rate=.2, invalid_rate=.2))
        for key in ('daily', 'funnel', 'cohorts', 'events'):
            self.assertEqual(clean[key], dirty[key])
        self.assertEqual(clean['summary']['quality_pass_rate'], 1)
        self.assertLess(dirty['summary']['quality_pass_rate'], 1)
        self.assertTrue(any('duplicate' in e['reason'] for e in dirty['quarantined']))
        self.assertTrue(any('unknown user' in e['reason'] for e in dirty['quarantined']))
        self.assertTrue(any('integer cents' in e['reason'] for e in dirty['quarantined']))
        self.assertTrue(any(c['failed'] > 0 for c in dirty['quality'] if c['id'] == 'relationships'))

    def test_empty_conversion_populations_and_cohort_censoring(self):
        for changes in (dict(activation_rate=0), dict(payment_rate=0)):
            run = run_simulation(SimulationConfig(**changes))
            self.assertEqual(run['summary']['paying_users'], 0)
            self.assertEqual(run['summary']['revenue_cents'], 0)
            self.assertEqual(run['summary']['churn_rate'], 0)
            self.assertEqual(run['cohorts'], [])
        run = run_simulation(SimulationConfig(days=8, daily_signups=5, activation_rate=1, payment_rate=1, churn_rate=0))
        self.assertEqual(run['cohorts'][0]['retention'][:3], [1, 1, None])
        self.assertEqual(run['cohorts'][-1]['retention'][:2], [1, None])

    def test_actual_lifecycle_schema_and_reference_rejection(self):
        config = SimulationConfig(days=7, daily_signups=5, activation_rate=1, payment_rate=1, duplicate_rate=0, invalid_rate=0)
        raw = generate_events(config)
        base = next(e for e in raw if e['event_type'] == 'signup')
        def event(identifier, hour, kind, **changes):
            return dict(base, event_id=identifier, occurred_at=f'2025-01-01T{hour}:00:00Z', event_type=kind, **changes)
        injected = [base, event('early-payment', '08', 'payment', amount_cents=1900 if base['plan'] == 'starter' else 4900),
                    event('churn-before-payment', '10', 'churn'),
                    event('bad-money', '10', 'activation', amount_cents=0.0),
                    event('bad-user', '10', 'activation', user_id='???'),
                    event('bad-date', '25', 'activation'), event('bad-plan', '10', 'activation', plan=[]),
                    event('valid-activation', '11', 'activation'), event('repeat-activation', '12', 'activation')]
        accepted, quarantine, _, checks = validate_events(injected, config)
        self.assertEqual([e['event_id'] for e in accepted], [base['event_id'], 'valid-activation'])
        self.assertEqual(sum(c['failed'] for c in checks), 7)
        self.assertTrue(any('signup must precede' in e['reason'] for e in quarantine))
        self.assertTrue(any('churn requires' in e['reason'] for e in quarantine))

    def test_export_parity_and_atomic_failure_preserves_existing(self):
        catalog = build_catalog()
        self.assertEqual([r['scenario']['id'] for r in catalog['runs']], ['baseline', 'acquisition', 'retention', 'quality'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.json'
            write_json_atomic(catalog, path)
            content = path.read_bytes()
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o644)
            subprocess.run([sys.executable, '-m', 'playground', 'export', '--output', str(path)], check=True, capture_output=True)
            self.assertEqual(content, path.read_bytes())
            self.assertEqual(catalog, json.loads(content))
            with self.assertRaises(ValueError):
                write_json_atomic({'bad': float('nan')}, path)
            self.assertEqual(content, path.read_bytes())
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_maximum_population_is_bounded_and_serializable(self):
        run = run_simulation(SimulationConfig(days=90, daily_signups=100, activation_rate=1, payment_rate=1, churn_rate=0, duplicate_rate=.2, invalid_rate=.2))
        self.assertEqual(run['summary']['signups'], 9000)
        self.assertEqual(run['summary']['active_customers'], 9000)
        self.assertEqual(len(run['daily']), 90)
        self.assertLess(run['pipeline'][0]['input_count'], 70000)
        json.dumps(run, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
