import asyncio
from datetime import datetime
import uuid
from typing import List, Dict, Optional, Tuple
import httpx
from pydantic import BaseModel, Field

from .new_fake_data_generator_helpers import (
    BASE_URL,
    logger,
    check_api_connection
)
from .odds_maker import OddsMaker
from .user import User, Shop, generate_fake_user

async def process_in_chunks(tasks, chunk_size=100):
    results = []
    total_tasks = len(tasks)
    logger.info(f"Processing {total_tasks} tasks in chunks of {chunk_size}")
    try:
        for i in range(0, total_tasks, chunk_size):
            chunk = tasks[i:i + chunk_size]
            logger.debug(f"Processing chunk {i // chunk_size + 1} of {(total_tasks + chunk_size - 1) // chunk_size}")
            chunk_results = await asyncio.gather(*chunk, return_exceptions=True)
            results.extend([r for r in chunk_results if not isinstance(r, Exception)])
            errors = [r for r in chunk_results if isinstance(r, Exception)]
            if errors:
                logger.error(f"Encountered {len(errors)} errors in chunk {i // chunk_size + 1}")
                for error in errors[:5]:  # Log first 5 errors
                    logger.error(f"Error in chunk: {str(error)}")
        logger.info(f"Finished processing all chunks. Total successful results: {len(results)}")
        return results
    except Exception as e:
        logger.error(f"Error in process_in_chunks: {str(e)}")
        raise

async def generate_users(n: int, current_date: datetime) -> Optional[List[User]]:
    logger.info(f"Attempting to generate {n} users for date {current_date}")
    try:
        if await check_api_connection(BASE_URL):
            async with httpx.AsyncClient() as client:
                tasks = [generate_fake_user(current_date, client) for _ in range(n)]
                processed_users = await process_in_chunks(tasks)
            valid_users = [user for user in processed_users if user is not None]
            logger.info(f"Successfully generated {len(valid_users)} users out of {n} attempts")
            return valid_users
        else:
            logger.warning("API connection failed. Returning None for generated users.")
            return None
    except Exception as e:
        logger.error(f"Error in generate_users: {str(e)}")
        return None

async def generate_shops(users: List[User], n: int, current_date: datetime) -> Optional[List[Shop]]:
    logger.info(f"Attempting to generate shops for {len(users)} users, max {n} shops, for date {current_date}")
    try:
        if await check_api_connection(BASE_URL):
            async with httpx.AsyncClient() as client:
                tasks = [user.create_shop(current_date, client) for user in users]
                processed_shops = await process_in_chunks(tasks)
            valid_shops = [shop for shop in processed_shops if shop is not None]
            logger.info(f"Successfully generated {len(valid_shops)} shops out of {len(users)} attempts")
            return valid_shops
        else:
            logger.warning("API connection failed. Returning None for generated shops.")
            return None
    except Exception as e:
        logger.error(f"Error in generate_shops: {str(e)}")
        return None

async def deactivate_shops(shops: List[Shop], n: int, current_date: datetime) -> Optional[List[Shop]]:
    logger.info(f"Attempting to deactivate {len(shops)} shops, max {n}, for date {current_date}")
    try:
        if await check_api_connection(BASE_URL):
            async with httpx.AsyncClient() as client:
                tasks = [shop.deactivate(current_date, None, client) for shop in shops]
                processed_shops = await process_in_chunks(tasks)
            deactivated_shops = [shop for shop in processed_shops if shop is not None]
            logger.info(f"Successfully deactivated {len(deactivated_shops)} shops out of {len(shops)} attempts")
            return deactivated_shops
        else:
            logger.warning("API connection failed. Returning None for deactivated shops.")
            return None
    except Exception as e:
        logger.error(f"Error in deactivate_shops: {str(e)}")
        return None

async def deactivate_users(users: List[User], n: int, current_date: datetime) -> Optional[Tuple[List[User], List[Shop]]]:
    logger.info(f"Attempting to deactivate {len(users)} users, max {n}, for date {current_date}")
    try:
        if await check_api_connection(BASE_URL):
            async with httpx.AsyncClient() as client:
                tasks = [user.deactivate(current_date, None, client) for user in users]
                processed_users = await process_in_chunks(tasks)
            r_users = []
            r_shops = []
            for user, shops in processed_users:
                if user is not None and shops is not None:
                    r_users.append(user)
                    r_shops.extend(shops)
            logger.info(f"Successfully deactivated {len(r_users)} users and {len(r_shops)} associated shops")
            return r_users, r_shops
        else:
            logger.warning("API connection failed. Returning None for deactivated users and shops.")
            return None
    except Exception as e:
        logger.error(f"Error in deactivate_users: {str(e)}")
        return None