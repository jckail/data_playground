from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from .routes import users, events, admin, shops, invoices, payments
from .core.scheduler import start_scheduler, shutdown_scheduler
from .tasks.fake_data_generator import run_async_generate_fake_data
import logging

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.include_router(users.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(shops.router)
app.include_router(events.router)
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return """
    <html>
        <body>
            <h1>Hello World</h1>
            <form action="/trigger_fake_data" method="post">
                <input type="submit" value="Generate Fake Data">
            </form>
            <br>
            <a href="http://0.0.0.0:8000/docs" target="_blank">
                <button>Go to Docs</button>
            </a>
            <a href="http://0.0.0.0:8501" target="_blank">
                <button>Go to Streamlit Dashboard</button>
            </a>
        </body>
    </html>
    """

@app.post("/trigger_fake_data")
async def trigger_fake_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_async_generate_fake_data)
    return {"message": "Fake data generation triggered"}