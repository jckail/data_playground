import asyncio
from datetime import datetime
from typing import List, Dict
import httpx
import pytz
from faker import Faker
import logging
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
        
