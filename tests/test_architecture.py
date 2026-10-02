"""Executable scheduler, source fidelity and publication contracts."""
import copy
import json
import sqlite3
import subprocess
import sys
import unittest

from playground.analytics import COHORT_SQL, CUSTOMERS_SQL, DAILY_SQL, aggregate
from playground.architecture import build_architecture, execute_dag, fingerprint_payload, reconcile, topological_order
from playground.catalog import build_catalog
from playground.config import SimulationConfig
from playground.exploration import build_exploration
from playground.pipeline import validate_events
from playground.simulation import generate_events


class ArchitectureTests(unittest.TestCase):
    def test_executable_runs_retry_and_independent_failure(self):
        architecture = build_architecture()
        dag = architecture['dags'][0]
        normal, retry, failed = dag['runs']
        self.assertEqual(normal['fingerprint'], retry['fingerprint'])
        self.assertEqual(len(normal['fingerprint']), 64)
        self.assertTrue(normal['published'])
        self.assertTrue(retry['published'])
        self.assertFalse(failed['published'])
        self.assertIsNone(failed['fingerprint'])
        self.assertEqual([(t['attempt'], t['status']) for t in retry['trace'] if t['task_id'] == 'analytics'], [(1, 'failed'), (2, 'success')])
        self.assertEqual([(t['task_id'], t['status']) for t in failed['trace']], [('generate', 'success'), ('validate', 'failed'), ('analytics', 'blocked'), ('exploration', 'success'), ('reconcile', 'blocked'), ('publish', 'blocked')])
        self.assertTrue(all(t['attempt'] == 0 for t in failed['trace'] if t['status'] == 'blocked'))
        self.assertEqual(architecture, build_architecture())
        self.assertEqual(architecture, build_catalog()['architecture'])
        json.dumps(architecture, allow_nan=False)

    def test_graph_rejection_happens_before_callbacks(self):
        calls = []
        def callback(outputs, attempt):
            calls.append(attempt)
            return None, 'done'
        cases = [[dict(id='a', depends_on=['missing'], max_attempts=1)],
                 [dict(id='a', depends_on=['b'], max_attempts=1), dict(id='b', depends_on=['a'], max_attempts=1)],
                 [dict(id='a', depends_on=[], max_attempts=1), dict(id='a', depends_on=[], max_attempts=1)]]
        for tasks in cases:
            with self.assertRaises(ValueError):
                execute_dag(tasks, {'a': callback, 'b': callback})
        self.assertEqual(calls, [])
        with self.assertRaises(ValueError):
            execute_dag([dict(id='a', depends_on=[], max_attempts=1)], {})

    def test_permanent_errors_do_not_retry_and_order_is_stable(self):
        tasks = [dict(id='dependent', depends_on=['source'], max_attempts=2), dict(id='source', depends_on=[], max_attempts=3), dict(id='independent', depends_on=[], max_attempts=1)]
        calls = []
        def fail(outputs, attempt):
            calls.append(('source', attempt))
            raise ValueError('permanent contract failure')
        def independent(outputs, attempt):
            calls.append(('independent', attempt))
            return 'ok', 'executed'
        outputs, trace = execute_dag(tasks, dict(source=fail, dependent=independent, independent=independent))
        self.assertEqual(calls, [('source', 1), ('independent', 1)])
        self.assertEqual(outputs, {'independent': 'ok'})
        self.assertEqual([t['id'] for t in topological_order(tasks)], ['source', 'dependent', 'independent'])
        self.assertEqual([t['status'] for t in trace], ['failed', 'blocked', 'success'])
        self.assertEqual(fingerprint_payload({'a': 1, 'b': 2}), fingerprint_payload({'b': 2, 'a': 1}))
        with self.assertRaises(ValueError):
            fingerprint_payload({'bad': float('nan')})

    def test_model_sql_executes_against_live_accepted_source(self):
        models = {m['id']: m for m in build_architecture()['models']}
        self.assertEqual(models['customers']['sql'], CUSTOMERS_SQL)
        self.assertEqual(models['daily']['sql'], DAILY_SQL)
        self.assertEqual(models['cohorts']['sql'], COHORT_SQL)
        accepted = validate_events(generate_events(SimulationConfig()), SimulationConfig())[0]
        with sqlite3.connect(':memory:') as db:
            db.execute(models['events']['sql'])
            db.executemany('INSERT INTO events VALUES (:event_id,:occurred_at,:user_id,:event_type,:amount_cents,:channel,:plan)', accepted)
            db.execute(models['customers']['sql'])
            for key in ('events', 'customers'):
                columns = [row[1] for row in db.execute(f'PRAGMA table_info({key})')]
                self.assertEqual(columns, [c['name'] for c in models[key]['columns']])
            self.assertTrue(db.execute(models['daily']['sql']).fetchall())
            self.assertTrue(db.execute(models['cohorts']['sql']).fetchall())
            self.assertEqual(db.execute('PRAGMA foreign_key_list(events)').fetchall(), [])
        self.assertEqual(models['daily']['kind'], 'artifact')
        self.assertEqual(models['cohorts']['kind'], 'artifact')
        self.assertTrue(all(dep in models for m in models.values() for dep in m['depends_on']))
        self.assertTrue(all(not models[key]['sql'] for key in ('products', 'shoppers', 'purchases', 'graph', 'vectors')))

    def test_publication_reconciliation_rejects_corrupted_payloads(self):
        config = SimulationConfig(days=7, daily_signups=5)
        raw = generate_events(config)
        accepted = validate_events(raw, config)[0]
        analytics = aggregate(accepted, config, len(raw))
        exploration = build_exploration()
        self.assertEqual(reconcile(analytics, exploration)['summary'], analytics[0])
        altered = copy.deepcopy(analytics)
        altered[0]['revenue_cents'] += 1
        with self.assertRaisesRegex(ValueError, 'revenue'):
            reconcile(altered, exploration)
        altered_graph = copy.deepcopy(exploration)
        next(edge for edge in altered_graph['graph']['edges'] if edge['relation'] == 'purchased')['weight'] += 1
        with self.assertRaisesRegex(ValueError, 'graph'):
            reconcile(analytics, altered_graph)

    def test_cli_replays_all_failure_modes(self):
        for failure, published in [('none', True), ('analytics-transient', True), ('validation-permanent', False)]:
            process = subprocess.run([sys.executable, '-m', 'playground', 'orchestrate', '--failure', failure], check=True, capture_output=True, text=True)
            self.assertEqual(json.loads(process.stdout)['published'], published)


if __name__ == '__main__':
    unittest.main()
