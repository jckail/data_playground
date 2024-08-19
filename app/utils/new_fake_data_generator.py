import asyncio
from datetime import datetime
import uuid
from typing import List, Dict
import httpx


from app.utils.new_fake_data_generator_models import User, generate_fake_user,  Shop, ActionCounter, BaseDataStore, BatchDataStore #everything
from app.utils.new_fake_data_generator_helpers import api_request, get_time, generate_event_time, check_api_connection, BASE_URL, logger

    

async def generate_users( n: int, current_date: datetime) -> List[User]:
    users = await asyncio.gather(*[generate_fake_user(current_date) for _ in range(n)])
    
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            processed_users = await asyncio.gather(*[user.call_create_user( client) for user in users])
        return [user for user in processed_users if user is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed users.")
        return users

async def main():
    data_store = BaseDataStore()


    current_date = get_time()
    users = await generate_users( 10, current_date)
    data_store.update_base_data_store(data_store, users)

    
    logger.info(f"Generated {len(users)} users")


    #stopping point was at the main of the claude generated file 
    

if __name__ == "__main__":
    
    asyncio.run(main(user_dict))


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