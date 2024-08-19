import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.tasks.fake_data_generator import run_async_generate_fake_data
#from app.tasks.generate_plots import generate_plots
from app.tasks.rollup_task import run_rollups_task

scheduler = AsyncIOScheduler()

# # Schedule fake data generation every 5 minutes
# scheduler.add_job(run_async_generate_fake_data, CronTrigger(minute='*/5'))


# Schedule plot generation every 5 minutes
#scheduler.add_job(generate_plots, CronTrigger(minute='*/5'))

# Schedule rollups task every 15 minutes
#scheduler.add_job(run_rollups_task, CronTrigger(minute='*/15'))

async def start_scheduler():
    scheduler.start()

async def shutdown_scheduler():
    scheduler.shutdown()

# Function to run the scheduler
def run_scheduler():
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)  # Set the new event loop as the current loop
    loop.run_until_complete(start_scheduler())
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        loop.run_until_complete(shutdown_scheduler())
        loop.close()
