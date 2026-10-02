"""Offline legacy regressions: no imports of database-connected app modules."""
import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    function = next(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    # Framework annotations/default Depends are irrelevant at this offline boundary.
    function.decorator_list = []
    function.returns = None
    for arg in function.args.args:
        arg.annotation = None
    function.args.defaults = [ast.Constant(None) for _ in function.args.defaults]
    isolated = ast.Module(body=[function], type_ignores=[])
    ast.fix_missing_locations(isolated)
    exec(compile(isolated, str(ROOT / path), 'exec'), namespace)
    return namespace[name]


class LegacyDashboardTests(unittest.TestCase):
    def test_health_uses_synchronous_session(self):
        executed = []
        check = load_function('app/main.py', 'health_check', {'text': str})
        self.assertEqual(check(SimpleNamespace(execute=lambda sql: executed.append(sql))), {'status': 'healthy'})
        self.assertEqual(executed, ['SELECT 1'])

    def test_rollup_empty_dates_preserves_not_found(self):
        class HttpError(Exception):
            def __init__(self, status_code, detail):
                self.status_code = status_code
        check = load_function('app/routes/create_rollups.py', 'create_rollups', {'text': str, 'HTTPException': HttpError, 'logger': logging.getLogger('test')})
        db = SimpleNamespace(execute=lambda sql: SimpleNamespace(fetchall=lambda: []))
        with self.assertRaises(HttpError) as error:
            check(SimpleNamespace(add_task=lambda *args: self.fail('No work should be queued')), db=db)
        self.assertEqual(error.exception.status_code, 404)

    def test_shops_use_their_own_dates_and_partial_series_survives(self):
        class Figure:
            def __init__(self): self.traces = []
            def add_trace(self, trace): self.traces.append(trace)
            def update_layout(self, **kwargs): pass
        async def query(sql):
            return [] if sql == 'users' else [{'partition_key': '2025-03-19', 'b': 7}]
        fn = load_function('streamlit_app/plots.py', 'create_users_shops_plot', {
            'go': SimpleNamespace(Figure=Figure, Scatter=lambda **kwargs: kwargs),
            'execute_query': query, 'users_query': 'users', 'shops_query': 'shops', 'logger': logging.getLogger('test')})
        fig, users, shops = asyncio.run(fn())
        self.assertEqual(fig.traces[1]['x'], ['2025-03-19'])
        self.assertEqual(fig.traces[1]['y'], [7])
        self.assertEqual(users, [])
        self.assertEqual(len(shops), 1)

    def test_database_failure_is_not_reported_as_empty(self):
        async def query(sql): raise RuntimeError('offline simulated database failure')
        fn = load_function('streamlit_app/plots.py', 'create_events_plot', {
            'execute_query': query, 'events_query': 'events', 'logger': logging.getLogger('test')})
        with self.assertRaisesRegex(RuntimeError, 'simulated database failure'):
            asyncio.run(fn())

    def test_home_missing_and_present_chart_fragments(self):
        try:
            from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
        except ImportError:
            self.skipTest('Legacy Jinja2 dependency is not installed')
        loader = FileSystemLoader(ROOT / 'app/templates')
        missing = Environment(loader=loader).get_template('index.html').render()
        self.assertEqual(missing.count('<strong>Report snapshot unavailable</strong>'), 3)
        present = Environment(loader=ChoiceLoader([DictLoader({'users_shops_plot.html': '<p>Existing report</p>'}), loader])).get_template('index.html').render()
        self.assertIn('<p>Existing report</p>', present)
        self.assertEqual(present.count('<strong>Report snapshot unavailable</strong>'), 2)


if __name__ == '__main__':
    unittest.main()
