import asyncio
from datetime import datetime, timedelta

from app.utils.fake_data.new_fake_data_generator_models import BaseDataStore
from app.routes.api_helpers import get_time
from app.models.odds_maker import OddsMaker

async def process_date_range( base, start_date: datetime, end_date: datetime, om = OddsMaker()):
    current_date = start_date
    while current_date <= end_date:
        print(f"Processing date: {current_date.date()}")
        await base.process_day(current_date, om)
        current_date += timedelta(days=1)
    base.analyze_trends()

async def main():
    base = BaseDataStore()
    end_date = get_time()
    start_date = end_date - timedelta(days=2)  # 365*2 Two years ago
    
    await process_date_range(base, start_date, end_date)

async def old_main():  #TODO replace main with a daily that takes in a datastore and a date
    base = BaseDataStore()
    current_date = get_time()
    await base.process_day(current_date)

if __name__ == "__main__":

    asyncio.run(main())

