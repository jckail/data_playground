import asyncio
import random
import httpx
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

async def generate_fake_data():
    current_time = datetime.now(pytz.utc)
    start_date = current_time - timedelta(minutes=5)  
    end_date = current_time

    payload = {
        "end_date": end_date.isoformat(),
        "max_fake_users_per_day": random.randint(1, 100),
        "max_first_shop_creation_percentage": 0.8,
        "max_multiple_shop_creation_percentage": 0.1,
        "max_shop_churn": 0.05,
        "max_user_churn": 0.01,
        "start_date": start_date.isoformat()
    }

    logger.info(f"Sending payload to generate fake data: {payload}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8000/generate_fake_data",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            logger.info(f"Generate fake data task completed. Status code: {response.status_code}")
            logger.info(f"Response content: {response.text}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            logger.error(f"Response content: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while requesting: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

def run_async_generate_fake_data():
    asyncio.run(generate_fake_data())
