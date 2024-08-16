import asyncio
import httpx
from datetime import datetime, timedelta
import random
from faker import Faker
import pytz
import logging
from dateutil.parser import parse
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


fake = Faker()
BASE_URL = "http://localhost:8000"  # Adjust if your API is hosted elsewhere


async def generate_event_time(current_date, day_start=None):
    try:
        # Convert day_start to datetime if it's a string
        if isinstance(day_start, str):
            day_start = parse(day_start)

        if day_start is None:
            day_start = datetime.combine(
                current_date, datetime.min.time()
            ).replace(tzinfo=pytz.UTC)
        elif isinstance(day_start, datetime):
            day_start = day_start.replace(tzinfo=pytz.UTC)
        else:
            raise ValueError(
                "day_start must be a datetime object, a valid datetime string, or None"
            )

        day_end = datetime.combine(current_date, datetime.max.time()).replace(
            tzinfo=pytz.UTC
        )
        return fake.date_time_between(
            start_date=day_start, end_date=day_end, tzinfo=pytz.UTC
        ).isoformat()
    except Exception as e:
        logger.error(
            f"Error generating event time: {e}, {day_start}, {type(day_start)}"
        )
        raise





async def process_tasks(client, tasks):
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
        return [
            result for result in results if not isinstance(result, Exception)
        ]
    except Exception as e:
        logger.error(f"Error processing tasks: {e}")
        raise


async def post_request(
    client, url, payload, error_message, semaphore=None, retries=3
):
    async with semaphore or asyncio.Semaphore(1):
        for attempt in range(retries):
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if 500 <= e.response.status_code < 600:
                    logger.warning(
                        f"Server error ({e.response.status_code}): {e}. Retrying..."
                    )
                    continue  # Retry on server errors
                else:
                    logger.error(f"{error_message}: {e}")
                    return None
            except httpx.RequestError as e:
                logger.error(f"Request failed: {e}. Retrying...")
                continue  # Retry on connection errors
            except Exception as e:
                logger.error(f"{error_message}: {e}")
                return None
        logger.error(f"Failed after {retries} retries for url: {url}")
        return None



def sampler(population:List, propensity, r= False) -> List:
    random.shuffle(population)

    if r:
        propensity = random.uniform(0, propensity)

    return      random.sample(
        population,
        int(len(population) * propensity),
    )