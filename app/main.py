from fastapi import FastAPI, BackgroundTasks, Request, Response,Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from .routes import users, events, admin, shops, invoices, payments
from .core.scheduler import start_scheduler, shutdown_scheduler
from .tasks.fake_data_generator import run_async_generate_fake_data
from .tasks.generate_plots import generate_plots
import logging
import sys
import os
from .database import  get_db,parse_event_time
from datetime import datetime
from .models import RequestResponseLog
import pytz
# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up templates
templates = Jinja2Templates(directory="app/templates")

app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(shops.router)
app.include_router(events.router)
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.get("/health/")
async def health_check():
    return {"status": "ok"}

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Regenerate the plots every time the index page is accessed
    generate_plots()
    
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/trigger_fake_data")
async def trigger_fake_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_async_generate_fake_data)
    return {"message": "Fake data generation triggered"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    db = next(get_db())  # Get the actual session from the generator
    method = request.method
    url = str(request.url)

    try:
        request_body = await request.body()
    except Exception:
        request_body = b''

    response = await call_next(request)

    status_code = response.status_code
    try:
        response_body = b"".join([chunk async for chunk in response.body_iterator])
    except Exception:
        response_body = b''

    try:

        log_entry = RequestResponseLog.create_with_partition(
            db,
            method=method,
            url=url,
            request_body=request_body.decode('utf-8'),
            response_body=response_body.decode('utf-8'),
            status_code=status_code,
            event_time=parse_event_time(datetime.utcnow().replace(tzinfo=pytz.UTC))
    )

        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log request/response: {e}")
    finally:
        db.close()

    return Response(content=response_body, status_code=status_code, headers=dict(response.headers))