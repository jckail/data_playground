"""Actual legacy chart/router integration with inert DB and outbound boundaries.

Optional runtime dependencies are installed by the focused legacy CI job.
This suite does not import app.main, start its scheduler, or open a database.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import date
import importlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
HAS_RUNTIME = all(importlib.util.find_spec(name) is not None for name in ['plotly', 'sqlalchemy', 'jinja2', 'fastapi', 'httpx'])


def source_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAS_RUNTIME, 'Focused legacy runtime dependencies not installed')
class LegacyRuntimeTests(unittest.TestCase):
    def test_real_plotly_shops_have_independent_axis(self):
        queries = ModuleType('queries')
        queries.users_query, queries.shops_query = 'users', 'shops'
        queries.events_query = queries.request_response_logs_query = 'unused'
        queries.get_sankey_query = lambda *args: 'unused'
        queries.execute_query = AsyncMock(side_effect=[
            [{'partition_key': date(2025, 1, 1), 'b': 3}],
            [{'partition_key': date(2025, 1, 3), 'b': 7}],
        ])
        with patch.dict(sys.modules, {'queries': queries}):
            plots = source_module('legacy_plots', 'streamlit_app/plots.py')
        figure, users, shops = asyncio.run(plots.create_users_shops_plot())
        self.assertEqual(tuple(figure.data[0].x), (date(2025, 1, 1),))
        self.assertEqual(tuple(figure.data[1].x), (date(2025, 1, 3),))
        self.assertEqual(tuple(figure.data[1].y), (7,))
        self.assertIn('Users', figure.to_json())

    def test_actual_query_retries_raise_instead_of_empty_rows(self):
        from sqlalchemy.exc import SQLAlchemyError
        db = ModuleType('db')

        @asynccontextmanager
        async def transaction():
            yield

        session = SimpleNamespace(begin=transaction, execute=AsyncMock(side_effect=SQLAlchemyError('fixture failure')))

        async def get_db():
            yield session

        db.get_db = get_db
        with patch.dict(sys.modules, {'db': db}):
            queries = source_module('legacy_queries', 'streamlit_app/queries.py')
        with self.assertRaises(SQLAlchemyError):
            asyncio.run(queries.execute_query('SELECT 1', max_retries=2, delay=0))
        self.assertEqual(session.execute.await_count, 2)

    def test_real_rollup_router_preserves_404_and_queues_only_selected_dates(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        database = ModuleType('app.database')
        database.get_db = lambda: None
        helpers = ModuleType('app.utils.helpers')
        helpers.post_request = AsyncMock()
        helpers.BASE_URL = 'https://fixture.invalid'
        with patch.dict(sys.modules, {'app.database': database, 'app.utils.helpers': helpers}):
            # Import the actual route module, not extracted/recompiled functions.
            with patch.dict(sys.modules):
                sys.modules.pop('app.routes.create_rollups', None)
                routes = importlib.import_module('app.routes.create_rollups')
        app = FastAPI()
        app.include_router(routes.router)
        rows = []
        session = SimpleNamespace(execute=lambda query: SimpleNamespace(fetchall=lambda: rows))
        app.dependency_overrides[database.get_db] = lambda: session
        client = TestClient(app)
        self.assertEqual(client.post('/create_rollups').status_code, 404)
        rows.append(SimpleNamespace(event_date=date(2025, 1, 3)))
        tasks = AsyncMock()
        with patch.object(routes, 'run_rollup', tasks):
            response = client.post('/create_rollups')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(tasks.await_count, 2)
        self.assertEqual([call.args[1] for call in tasks.await_args_list], ['user_snapshot', 'shop_snapshot'])
        self.assertEqual(helpers.post_request.await_count, 0)


if __name__ == '__main__':
    unittest.main()
