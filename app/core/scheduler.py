from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.tasks.fake_data_generator import run_async_generate_fake_data
from app.tasks.generate_plots import generate_plots
from app.tasks.rollup_task import run_rollups_task  # Import the new task function

scheduler = BackgroundScheduler()

# Schedule fake data generation every 5 minutes
scheduler.add_job(run_async_generate_fake_data, CronTrigger(minute='*/5'))

# Schedule plot generation every 5 minutes
scheduler.add_job(generate_plots, CronTrigger(minute='*/5'))

# Schedule rollups task every 15 minutes
scheduler.add_job(run_rollups_task, CronTrigger(minute='*/15'))

def start_scheduler():
    scheduler.start()

def shutdown_scheduler():
    scheduler.shutdown()
