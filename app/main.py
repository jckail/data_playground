from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from .routes import users, events, admin, shops, invoices, payments
from .core.scheduler import start_scheduler, shutdown_scheduler
from .tasks.fake_data_generator import run_async_generate_fake_data
import logging
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit_app import create_plot
import plotly.io as pio

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

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/trigger_fake_data")
async def trigger_fake_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_async_generate_fake_data)
    
    # Regenerate the plot
    fig = create_plot()
    plot_html = pio.to_html(fig, full_html=False)
    with open('app/templates/plot.html', 'w') as f:
        f.write(plot_html)
    
    return {"message": "Fake data generation triggered"}