import sys
import os
import asyncio
import random
from datetime import datetime, timedelta
import pytz
import logging
from typing import List, Dict
from faker import Faker
import httpx
import time

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from app.models import EventPropensity, FakeHelper

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()
BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')

class User:
    def __init__(self, id, email, event_time):
        self.id = id
        self.email = email
        self.event_time = event_time
        self.shops = []
        self.is_active = True

class Shop:
    def __init__(self, id, shop_owner_id, event_time, shop_name):
        self.id = id
        self.shop_owner_id = shop_owner_id
        self.event_time = event_time
        self.shop_name = shop_name

async def check_api_connection():
    logger.info(f"Checking API connection to {BASE_URL}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(BASE_URL)
            logger.info(f"API check status: {response.status_code}")
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.error(f"Error connecting to API: {e}")
            return False

async def generate_event_time(current_date: datetime) -> str:
    day_start = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=pytz.UTC)
    day_end = datetime.combine(current_date, datetime.max.time()).replace(tzinfo=pytz.UTC)
    return fake.date_time_between(start_date=day_start, end_date=day_end, tzinfo=pytz.UTC).isoformat()

async def api_request(client: httpx.AsyncClient, method: str, url: str, payload: Dict = None, timeout: int = 30) -> Dict:
    try:
        response = await client.request(method, url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
    except httpx.RequestError as e:
        logger.error(f"Request error for {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error for {url}: {e}")
    return None

async def create_fake_user(client: httpx.AsyncClient, current_date: datetime) -> User:
    email = fake.email()
    event_time = await generate_event_time(current_date)
    payload = {"email": email, "event_time": event_time}
    response = await api_request(client, "POST", f"{BASE_URL}/create_user/", payload)
    if response:
        return User(response["event_metadata"]["user_id"], email, event_time)
    return None

async def create_fake_shop(client: httpx.AsyncClient, user: User, current_date: datetime) -> Shop:
    event_time = await generate_event_time(current_date)
    shop_name = fake.company()
    payload = {"shop_owner_id": user.id, "shop_name": shop_name, "event_time": event_time}
    response = await api_request(client, "POST", f"{BASE_URL}/create_shop/", payload)
    if response:
        return Shop(response["event_metadata"]["shop_id"], user.id, event_time, shop_name)
    return None

async def deactivate_user(client: httpx.AsyncClient, user: User, current_date: datetime) -> bool:
    event_time = await generate_event_time(current_date)
    payload = {"identifier": user.id, "event_time": event_time}
    result = await api_request(client, "POST", f"{BASE_URL}/deactivate_user/", payload)
    if result is not None:
        user.is_active = False
        return True
    return False

async def delete_shop(client: httpx.AsyncClient, shop: Shop, current_date: datetime) -> bool:
    event_time = await generate_event_time(current_date)
    payload = {"shop_id": shop.id, "event_time": event_time}
    return await api_request(client, "POST", f"{BASE_URL}/delete_shop/", payload) is not None

async def handle_fake_data(client: httpx.AsyncClient, current_date: datetime, ep: EventPropensity, fh: FakeHelper) -> FakeHelper:
    logger.info(f"Handling fake data for {current_date}")
    
    # Create new users
    users_to_generate = int(random.uniform(0, ep.max_fake_users_per_day))
    logger.info(f"Attempting to create {users_to_generate} users")
    new_users = [user for user in await asyncio.gather(*[create_fake_user(client, current_date) for _ in range(users_to_generate)]) if user]
    fh.users.extend(new_users)
    fh.daily_users_created = len(new_users)
    logger.info(f"Successfully created {fh.daily_users_created} users")

    # Create shops for active users
    active_users = [user for user in fh.users if user.is_active]
    shop_tasks = [create_fake_shop(client, user, current_date) for user in active_users if random.random() < ep.max_first_shop_creation_percentage]
    new_shops = [shop for shop in await asyncio.gather(*shop_tasks) if shop]
    for shop in new_shops:
        next(user for user in active_users if user.id == shop.shop_owner_id).shops.append(shop)
    fh.shops.extend(new_shops)
    fh.daily_shops_created = len(new_shops)
    logger.info(f"Successfully created {fh.daily_shops_created} shops")

    # Handle user deactivations and related shop deletions
    users_to_deactivate = random.sample(active_users, int(len(active_users) * ep.max_user_churn))
    deactivation_results = await asyncio.gather(*[deactivate_user(client, user, current_date) for user in users_to_deactivate])
    deactivated_users = [user for user, result in zip(users_to_deactivate, deactivation_results) if result]
    
    shops_to_delete = [shop for user in deactivated_users for shop in user.shops]
    deletion_results = await asyncio.gather(*[delete_shop(client, shop, current_date) for shop in shops_to_delete])
    
    fh.daily_users_deactivated = len(deactivated_users)
    fh.daily_shops_deleted = sum(deletion_results)
    
    for user in deactivated_users:
        user.shops = []
    fh.shops = [shop for shop in fh.shops if shop not in shops_to_delete or not deletion_results[shops_to_delete.index(shop)]]

    logger.info(f"Deactivated {fh.daily_users_deactivated} users and deleted {fh.daily_shops_deleted} shops")

    # Handle additional shop deletions for active users
    active_shops = [shop for user in active_users for shop in user.shops]
    additional_shops_to_delete = random.sample(active_shops, int(len(active_shops) * ep.max_shop_churn))
    additional_deletion_results = await asyncio.gather(*[delete_shop(client, shop, current_date) for shop in additional_shops_to_delete])
    
    additional_deleted_shops = sum(additional_deletion_results)
    fh.daily_shops_deleted += additional_deleted_shops
    for user in active_users:
        user.shops = [shop for shop in user.shops if shop not in additional_shops_to_delete or not additional_deletion_results[additional_shops_to_delete.index(shop)]]
    fh.shops = [shop for shop in fh.shops if shop not in additional_shops_to_delete or not additional_deletion_results[additional_shops_to_delete.index(shop)]]

    logger.info(f"Additionally deleted {additional_deleted_shops} shops")

    logger.info(f"Completed handling fake data for {current_date}")
    return fh

async def generate_fake_data(current_date: datetime, ep: EventPropensity, fh: FakeHelper) -> Dict:
    start_time = datetime.now()
    logger.info(f"Starting fake data generation for {current_date} at {start_time}")

    async with fh.semaphore:
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                fh = await handle_fake_data(client, current_date, ep, fh)
            except Exception as e:
                logger.error(f"Error during fake data generation for {current_date}: {e}")

    end_time = datetime.now()
    elapsed_time = end_time - start_time
    logger.info(f"Completed fake data generation for {current_date}. Elapsed time: {elapsed_time}")

    return {
        "date": current_date,
        "users_created": fh.daily_users_created,
        "users_deactivated": fh.daily_users_deactivated,
        "shops_created": fh.daily_shops_created,
        "shops_deleted": fh.daily_shops_deleted
    }

async def run_data_generation(
    start_date: datetime,
    end_date: datetime,
    max_fake_users_per_day: int,
    max_user_churn: float,
    max_first_shop_creation_percentage: float,
    max_multiple_shop_creation_percentage: float,
    max_shop_churn: float,
    semaphore: int = 250,
):
    logger.info(f"Starting data generation from {start_date} to {end_date} with max_fake_users_per_day={max_fake_users_per_day}")

    ep = EventPropensity(
        max_fake_users_per_day,
        max_user_churn,
        max_first_shop_creation_percentage,
        max_multiple_shop_creation_percentage,
        max_shop_churn,
    )
    fh = FakeHelper(semaphore=semaphore)
    z = {}
    start_time = time.time()

    # Initialize totals
    total_users_created = 0
    total_users_deactivated = 0
    total_shops_created = 0
    total_shops_deleted = 0

    try:
        for i in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=i)
            logger.debug(f"Generating fake data for {current_date}")

            # Reset daily counts
            fh.reset_daily_counts()

            # Run the daily data generation process
            daily_result = await generate_fake_data(current_date, ep, fh)
            z[current_date] = daily_result

            # Accumulate daily totals into the overall totals
            total_users_created += daily_result['users_created']
            total_users_deactivated += daily_result['users_deactivated']
            total_shops_created += daily_result['shops_created']
            total_shops_deleted += daily_result['shops_deleted']

            logger.debug(f"Day {current_date}: Users Created = {daily_result['users_created']}, Users Deactivated = {daily_result['users_deactivated']}, Shops Created = {daily_result['shops_created']}, Shops Deleted = {daily_result['shops_deleted']}")

    except Exception as e:
        logger.error(f"Error during data generation: {str(e)}")
        raise

    # Calculate the total runtime
    end_time = time.time()
    run_time = end_time - start_time

    # Create the final summary
    summary_dict = {
        "total_users_created": total_users_created,
        "total_users_deactivated": total_users_deactivated,
        "total_active_users": len([user for user in fh.users if user.is_active]),
        "total_shops_created": total_shops_created,
        "total_shops_deleted": total_shops_deleted,
        "total_active_shops": len(fh.shops),
        "total_days": (end_date - start_date).days + 1,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "run_time": round(run_time, 4),
    }

    logger.info(f"Data generation complete. Summary: {summary_dict}")

    return summary_dict

if __name__ == "__main__":
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 10).date()
    asyncio.run(run_data_generation(
        start_date,
        end_date,
        max_fake_users_per_day=2500,
        max_user_churn=0.15,
        max_first_shop_creation_percentage=0.5,
        max_multiple_shop_creation_percentage=0.1,
        max_shop_churn=0.25,
        semaphore=350
    ))