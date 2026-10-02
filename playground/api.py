"""Bounded, synthetic-only service; independent of the legacy database application."""

from functools import lru_cache
from threading import BoundedSemaphore

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from playground.catalog import build_catalog
from playground.config import SimulationConfig
from playground.pipeline import run_simulation

MAX_BODY_BYTES = 4096
MAX_CONCURRENT_RUNS = 2
_slots = BoundedSemaphore(MAX_CONCURRENT_RUNS)


class BodyLimitMiddleware:
    """Count actual ASGI body bytes, including requests without Content-Length."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                response = JSONResponse({"detail": "Request body exceeds 4096 bytes"}, 413)
                return await response(scope, receive, send)
            body.extend(chunk)
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    seed: int = Field(default=42, ge=0, le=2147483647)
    days: int = Field(default=30, ge=7, le=90)
    daily_signups: int = Field(default=30, ge=5, le=100)
    activation_rate: float = Field(default=0.65, ge=0, le=1)
    payment_rate: float = Field(default=0.35, ge=0, le=1)
    churn_rate: float = Field(default=0.02, ge=0, le=0.2)
    duplicate_rate: float = Field(default=0.03, ge=0, le=0.2)
    invalid_rate: float = Field(default=0.02, ge=0, le=0.2)


app = FastAPI(title="Synthetic Data Playground", version="1.0.0")
app.add_middleware(BodyLimitMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic can include NaN/Infinity in the offending input. Do not echo
    # input values: they are neither needed for diagnostics nor valid JSON.
    details = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse({"detail": details}, status_code=422)


def _bounded_work(work):
    # This runs inside FastAPI's worker thread. The worker retains its slot even
    # when the requesting client disconnects or its coroutine is cancelled.
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, "Simulation capacity reached; retry later", headers={"Retry-After": "1"})
    try:
        return work()
    finally:
        _slots.release()


@lru_cache(maxsize=1)
def _catalog():
    return build_catalog()


@app.get("/health")
async def health():
    return {"status": "ok", "schema_version": 1, "engine_version": "1.0.0", "synthetic": True}


@app.get("/api/catalog")
def catalog():
    return _bounded_work(_catalog)


@app.post("/api/simulate")
def simulate(request: SimulationRequest):
    config = SimulationConfig(**request.model_dump())
    return _bounded_work(lambda: run_simulation(config))
