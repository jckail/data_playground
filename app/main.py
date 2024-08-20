from fastapi import FastAPI, BackgroundTasks, Request, Response, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from .routes import create_rollups, users, events, shops, invoices, payments, user_snapshot, shop_snapshot, generate_fake_data
from app.core.scheduler import run_scheduler
import threading
from .tasks.fake_data_generator import run_async_generate_fake_data
import logging
import sys
import os
from .database import get_db, parse_event_time, create_db_engine
from datetime import datetime
from .models import RequestResponseLog
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import psutil
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up templates
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(shops.router)
app.include_router(events.router)
app.include_router(create_rollups.router)
app.include_router(user_snapshot.router)
app.include_router(shop_snapshot.router)
app.include_router(generate_fake_data.router)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests')
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency')
ENDPOINT_COUNTERS = {}

# Function to sanitize metric names
def sanitize_metric_name(name: str) -> str:
    # Replace invalid characters with underscores
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure the name does not start with a digit
    if name and name[0].isdigit():
        name = f'_{name}'
    return name

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    # General request count and latency
    REQUEST_COUNT.inc()
    with REQUEST_LATENCY.time():
        response = await call_next(request)

    # Increment the counter for the specific endpoint
    endpoint = request.url.path
    sanitized_metric_name = sanitize_metric_name(endpoint.strip('/').replace('/', '_'))

    if sanitized_metric_name not in ENDPOINT_COUNTERS:
        metric_name = f"http_requests_total_{sanitized_metric_name}"
        ENDPOINT_COUNTERS[sanitized_metric_name] = Counter(metric_name, f'Total HTTP Requests to {endpoint}')
    
    ENDPOINT_COUNTERS[sanitized_metric_name].inc()

    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logging.error(f"An error occurred: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred"},
    )

@app.get("/health/")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {str(e)}")

@app.on_event("startup")
async def startup_event():
    # Check disk space
    if psutil.disk_usage('/').percent > 80:
        logging.warning("Disk usage is above 80%")
    
    # Check database connection
    try:
        await create_db_engine()
        logging.info("Successfully connected to the database")
    except Exception as e:
        logging.error(f"Failed to connect to database: {str(e)}")

    # Start the scheduler in a separate thread
    threading.Thread(target=run_scheduler, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    # The scheduler will be shut down when the main thread exits
    pass

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/auto_refresh_fake_data")
async def auto_refresh_fake_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_async_generate_fake_data)
    return {"message": "Fake data generation triggered"}


# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     async for db in get_db():
#         method = request.method
#         url = str(request.url)

#         try:
#             request_body = await request.body()
#         except Exception:
#             request_body = b''

#         response = await call_next(request)

#         status_code = response.status_code
#         try:
#             response_body = b"".join([chunk async for chunk in response.body_iterator])
#         except Exception:
#             response_body = b''

#         try:
#             log_entry = await RequestResponseLog.create_with_partition(
#                 db,
#                 method=method,
#                 url=url,
#                 request_body=request_body.decode('utf-8'),
#                 response_body=response_body.decode('utf-8'),
#                 status_code=status_code,
#                 event_time=await parse_event_time(datetime.utcnow().replace(tzinfo=pytz.UTC))
#             )

#             db.add(log_entry)
#             await db.commit()
#         except Exception as e:
#             logger.error(f"Failed to log request/response: {e}")
#         finally:
#             await db.close()

#     return Response(content=response_body, status_code=status_code, headers=dict(response.headers))