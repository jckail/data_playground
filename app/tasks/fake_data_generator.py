import asyncio
import random
import httpx
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)



async def task_generate_fake_data():
    current_time = datetime.now(pytz.utc)
    start_date = current_time - timedelta(day=1)  
    end_date = current_time

    payload = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
                "max_fake_users_per_day": 100,
                "max_fake_shops_per_day": 100,

                "max_user_growth_rate": 0.2,
                "max_shop_growth_rate": 0.2,

                "user_shop_population": 0.5,
                "shop_creation_chance": 0.8,
                
                "user_churn_chance": 0.2,
                "shop_churn_chance": 0.3,
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
    asyncio.run(task_generate_fake_data())
