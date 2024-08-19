import asyncio
from datetime import datetime
import uuid
from typing import List, Dict
import httpx


from app.utils.fake_data.new_fake_data_generator_models import User, generate_fake_user,  Shop, ActionCounter, BaseDataStore, BatchDataStore, OddsMaker
from app.utils.fake_data.new_fake_data_generator_helpers import api_request, get_time, generate_event_time, check_api_connection, BASE_URL, logger

    


    




async def main(base, current_date):  #TODO replace main with a daily that takes in a datastore and a date

    
    await base.process_day(current_date)

    

if __name__ == "__main__":
    base = BaseDataStore()
    current_date = get_time() #TODO replace main with a daily that takes in a datastore and a date
    asyncio.run(main(base, current_date))


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