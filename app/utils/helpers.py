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
        logger.debug(f"Generating event time for date {current_date} with day_start {day_start}")

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
        event_time = fake.date_time_between(
            start_date=day_start, end_date=day_end, tzinfo=pytz.UTC
        ).isoformat()

        logger.debug(f"Generated event time: {event_time}")
        return event_time
    except Exception as e:
        logger.error(
            f"Error generating event time: {e}, day_start={day_start}, type={type(day_start)}"
        )
        raise

async def process_tasks(client, tasks):
    try:
        logger.info(f"Processing {len(tasks)} tasks")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
        successful_results = [result for result in results if not isinstance(result, Exception)]
        logger.info(f"Successfully processed {len(successful_results)}/{len(tasks)} tasks")
        return successful_results
    except Exception as e:
        logger.error(f"Error processing tasks: {e}")
        raise

async def post_request(client, url, payload, error_message, semaphore=None):
    if semaphore is None:
        semaphore = asyncio.Semaphore(250)  # Default value if semaphore is not provided
    
    async with semaphore:
        try:
            logger.debug(f"Sending POST request to {url} with payload: {payload}")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            logger.debug(f"Received response: {response.json()}")
            return response.json()
        except httpx.HTTPStatusError as e:
            if 500 <= e.response.status_code < 600:
                logger.warning(
                    f"Server error ({e.response.status_code}): {e}. ."
                )
            else:
                logger.error(f"{error_message}: HTTP error {e.response.status_code}: {e}")
                return None
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}. ")
        except Exception as e:
            logger.error(f"{error_message}: Unexpected error: {e}")
            return None


def sampler(population: List, propensity, r=False) -> List:
    try:
        logger.debug(f"Sampling from population of size {len(population)} with propensity {propensity}, randomize: {r}")
        random.shuffle(population)

        if r:
            propensity = random.uniform(0, propensity)

        sample_size = int(len(population) * propensity)
        sampled_list = random.sample(population, sample_size)
        logger.debug(f"Sampled {len(sampled_list)} items from population")
        return sampled_list
    except Exception as e:
        logger.error(f"Error in sampling: {e}")
        raise
