import asyncio
from datetime import datetime, timedelta
import uuid
from typing import List, Dict
import httpx

from app.utils.fake_data.new_fake_data_generator_models import BaseDataStore
from app.utils.fake_data.new_fake_data_generator_helpers import get_time

async def process_date_range(base: BaseDataStore, start_date: datetime, end_date: datetime):
    current_date = start_date
    while current_date <= end_date:
        print(f"Processing date: {current_date.date()}")
        await base.process_day(current_date)
        current_date += timedelta(days=1)
    base.analyze_trends()

async def main():
    base = BaseDataStore()
    end_date = get_time()
    start_date = end_date - timedelta(days=365*2)  # 365*2 Two years ago
    
    await process_date_range(base, start_date, end_date)

async def old_main():  #TODO replace main with a daily that takes in a datastore and a date
    base = BaseDataStore()
    current_date = get_time()
    await base.process_day(current_date)

if __name__ == "__main__":
    # base = BaseDataStore()
    # current_date = get_time() #TODO replace main with a daily that takes in a datastore and a date
    # asyncio.run(main(base, current_date))
    asyncio.run(main())

    """

    after taking a step back i think that sql model is a better paradigm
    1. entity mapping with relationship
    2. easier to query 
    3. easier to update
    4. easier to delete


    FLOW --> 
    1. Create User
    2. Given User creates shops
    3. Logs to "global_events" too for tracking


    1. Create User

    2. Inserts Record into User Table

    3. Inserts Record into Global Event Table
    

    """