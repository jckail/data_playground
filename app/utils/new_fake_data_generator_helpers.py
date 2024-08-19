import asyncio
from datetime import datetime
import pytz
from typing import Dict
from faker import Faker
import logging
import httpx
import os
import random

fake = Faker()

BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

def get_time():
    return datetime.now(pytz.UTC)

def generate_event_time(current_date: datetime) -> datetime:
    return fake.date_time_between_dates(
        datetime_start=current_date.replace(hour=0, minute=0, second=0, microsecond=0),
        datetime_end=current_date.replace(hour=23, minute=59, second=59, microsecond=999999),
        tzinfo=pytz.UTC
    )

async def check_api_connection(url: str) -> bool:
    health_check_url = f"{url.rstrip('/')}/health/"
    logger.info(f"Checking API connection to {health_check_url}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(health_check_url)
            logger.info(f"API check status: {response.status_code}")
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.error(f"Error connecting to API: {e}")
            return False
        

class odds_maker:
    def __init__(self, 
        max_fake_users_per_day=2000,
        max_fake_shops_per_day=2000,

        max_user_growth_rate=0.2,
        max_shop_growth_rate=0.2,
        user_shop_population=0.5,
        shop_creation_chance=0.8,
        
        user_churn_chance=0.2,
        shop_churn_chance=0.3
        
        
        ):

        self.max_fake_users_per_day = max_fake_users_per_day
        self.max_fake_shops_per_day = max_fake_shops_per_day
        self.max_user_growth_rate = max_user_growth_rate
        self.max_shop_growth_rate = max_shop_growth_rate
        self.user_shop_population = user_shop_population
        self.shop_creation_chance = shop_creation_chance
        self.user_churn_chance = user_churn_chance
        self.shop_churn_chance = shop_churn_chance
        self.shops_to_generate = int(random.uniform(0, max_fake_shops_per_day)
        )   

    async def gen_prop(self, p_list, propensity, max_value=None, r=False):
        population = len(p_list)
        if population == 0:
            return max_value

        if not max_value:
            max_value = population

        if r:
            propensity = random.uniform(0, propensity)

        return min(int(len(population) * propensity), max_value)
    
    async def list_randomizer(self, input_list):
        for _ in range(int(random.uniform(1, 3))):
            input_list = random.shuffle(input_list)
        return input_list

    async def generate_fake_user_growth_amount(self, user_list):
        return await self.gen_prop(user_list, self.max_user_growth_rate, self.max_fake_users_per_day)
    
    async def generate_fake_shop_growth(self, user_list, shop_list):
        num_shops_to_create = await self.gen_prop(shop_list, self.max_shop_growth_rate, self.max_fake_shops_per_day)
        user_list = self.list_randomizer(self, user_list)
        return user_list[:num_shops_to_create]
    
    async def generate_fake_shop_churn(self, shop_list):
        num_shops_to_del = await self.gen_prop(shop_list, self.shop_churn_chance, self.max_fake_shops_per_day)
        shop_list = self.list_randomizer(self, shop_list)
        return shop_list[:num_shops_to_del]
    
    # async def generate_fake_shop_churn(self, shop_list):
    #     num_shops_to_del = await self.gen_prop(shop_list, self.shop_churn_chance, self.max_fake_shops_per_day)
    #     shop_list = self.list_randomizer(self, shop_list)
    #     return shop_list[:num_shops_to_del]