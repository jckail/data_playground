"""Tests target only the independent synthetic service, never legacy DB scripts."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from playground import api


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def test_health_and_catalog(self):
        self.assertTrue(self.client.get("/health").json()["synthetic"])
        response = self.client.get("/api/catalog")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["schema_version"], 1)
        self.assertEqual(len(response.json()["runs"]), 4)

    def test_repeatable_simulation(self):
        config = {"seed": 9, "days": 7, "daily_signups": 5}
        first = self.client.post("/api/simulate", json=config)
        second = self.client.post("/api/simulate", json=config)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(first.json()["summary"]["signups"], 35)

    def test_invalid_inputs(self):
        cases = [
            {"seed": -1}, {"seed": 2147483648}, {"seed": True},
            {"seed": "42"}, {"days": 6}, {"days": 91}, {"days": 7.5},
            {"daily_signups": 4}, {"daily_signups": 101},
            {"activation_rate": -0.01}, {"payment_rate": 1.01},
            {"churn_rate": 0.21}, {"duplicate_rate": -0.1},
            {"invalid_rate": 0.21}, {"sql": "select 1"},
            {"start_date": "2026-01-01"}, {"payment_rate": True},
        ]
        for config in cases:
            with self.subTest(config=config):
                self.assertEqual(self.client.post("/api/simulate", json=config).status_code, 422)

    def test_nonfinite_and_malformed_json(self):
        for body in ['{"payment_rate":NaN}', '{"payment_rate":Infinity}', '{"payment_rate":-Infinity}', '{']:
            with self.subTest(body=body):
                response = self.client.post("/api/simulate", content=body, headers={"Content-Type": "application/json"})
                self.assertEqual(response.status_code, 422)

    def test_body_size(self):
        response = self.client.post("/api/simulate", content=b" " * (api.MAX_BODY_BYTES + 1))
        self.assertEqual(response.status_code, 413)

    def test_streamed_body_without_length_is_bounded(self):
        messages = [
            {"type": "http.request", "body": b"x" * 3000, "more_body": True},
            {"type": "http.request", "body": b"x" * 2000, "more_body": False},
        ]
        sent = []
        reached = []

        async def receive():
            return messages.pop(0)

        async def send(message):
            sent.append(message)

        async def downstream(scope, receive, send):
            reached.append(True)

        asyncio.run(api.BodyLimitMiddleware(downstream)({"type": "http", "headers": []}, receive, send))
        self.assertFalse(reached)
        self.assertEqual(sent[0]["status"], 413)

    def test_capacity_and_release_after_failure(self):
        semaphore = threading.BoundedSemaphore(1)
        with patch.object(api, "_slots", semaphore):
            semaphore.acquire()
            try:
                response = self.client.post("/api/simulate", json={})
                self.assertEqual(response.status_code, 429)
                self.assertEqual(response.headers["retry-after"], "1")
            finally:
                semaphore.release()
            with patch.object(api, "run_simulation", side_effect=RuntimeError("test")):
                with self.assertRaises(RuntimeError):
                    self.client.post("/api/simulate", json={})
            self.assertTrue(semaphore.acquire(blocking=False))
            semaphore.release()

    def test_cancelled_waiter_does_not_release_worker_slot(self):
        entered = threading.Event()
        finish = threading.Event()
        semaphore = threading.BoundedSemaphore(1)

        def work():
            entered.set()
            finish.wait(timeout=5)
            return "done"

        async def exercise():
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = loop.run_in_executor(pool, api._bounded_work, work)
                try:
                    for _ in range(100):
                        if entered.is_set():
                            break
                        await asyncio.sleep(0.01)
                    self.assertTrue(entered.is_set())
                    future.cancel()
                    with self.assertRaises(HTTPException) as error:
                        api._bounded_work(lambda: None)
                    self.assertEqual(error.exception.status_code, 429)
                finally:
                    finish.set()
            self.assertEqual(api._bounded_work(lambda: "next"), "next")

        with patch.object(api, "_slots", semaphore):
            asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
