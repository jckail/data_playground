from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.tasks.fake_data_generator import run_async_generate_fake_data

scheduler = BackgroundScheduler()
scheduler.add_job(run_async_generate_fake_data, CronTrigger(minute='*/5'))  # Run every 5 minutes

def start_scheduler():
    scheduler.start()

def shutdown_scheduler():
    scheduler.shutdown()