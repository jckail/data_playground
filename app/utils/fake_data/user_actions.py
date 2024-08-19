import asyncio
from datetime import datetime
import uuid
from typing import List, Dict
import httpx
from pydantic import BaseModel, Field


from .new_fake_data_generator_helpers import (
    BASE_URL,
    logger,
    check_api_connection

)
from .odds_maker import OddsMaker
from .user import User, Shop, generate_fake_user



#NOTE: This was broken out because these are not models but rather functions that interact with the models that are not suitable to be methods
#NOTE: CONT> That means that each one of these functions should handle  the Oddsmaker for each function (ie be passed an instance of the odds maker)



async def process_in_chunks(tasks, chunk_size=100):
    results = []
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk)
        results.extend(chunk_results)
    return results

async def generate_users(n: int, current_date: datetime) -> List[User]:
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            tasks = [generate_fake_user(current_date, client) for _ in range(n)]
            processed_users = await process_in_chunks(tasks)
        return [user for user in processed_users if user is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed users.")
        return None

async def generate_shops(users, n: int, current_date: datetime) -> List[User]:
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            tasks = [user.create_shop(current_date, client) for user in users]
            processed_shops = await process_in_chunks(tasks)
        return [shop for shop in processed_shops if shop is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed shops.")
        return None

async def deactivate_shops(shops, n: int, current_date: datetime) -> List[User]:
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            tasks = [shop.deactivate(current_date, None, client) for shop in shops]
            processed_shops = await process_in_chunks(tasks)
        return [shop for shop in processed_shops if shop is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed shops.")
        return None

async def deactivate_users(users, n: int, current_date: datetime) -> List[User]:
    r_users = []
    r_shops = []

    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            tasks = [user.deactivate(current_date, None, client) for user in users]
            processed_users = await process_in_chunks(tasks)
            for user, shops in processed_users:
                if user is not None and shops is not None:
                    r_users.append(user)
                    r_shops += shops
        print('xxxxxx')
        return r_users, r_shops
    else:
        logger.warning("API connection failed. Returning unprocessed shops.")
        return None