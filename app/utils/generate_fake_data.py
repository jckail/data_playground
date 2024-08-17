import asyncio
import httpx
from datetime import datetime, timedelta

from ..models import EventPropensity, FakeHelper
from .helpers import logger
from .fake_users import handle_users
from .fake_shops import handle_shops

async def generate_fake_data(
    current_date,
    z: dict,
    ep: EventPropensity = EventPropensity(),
    fh: FakeHelper = FakeHelper()
):
    try:
        # Record the start time for logging
        start_time = datetime.now()
        logger.info(f"Starting fake data generation for {current_date} at {start_time}")

        async with httpx.AsyncClient() as client:
            # Handle users
            try:
                logger.info(f"Handling users for {current_date}")
                z[current_date] = await handle_users(client, current_date, ep, fh)
                logger.info(f"Users handled successfully for {current_date}")
            except Exception as user_error:
                logger.error(f"Error handling users for {current_date}: {user_error}")
                raise

            # Handle shops
            try:
                logger.info(f"Handling shops for {current_date}")
                z[current_date] = await handle_shops(client, current_date, ep, z[current_date])
                logger.info(f"Shops handled successfully for {current_date}")
            except Exception as shop_error:
                logger.error(f"Error handling shops for {current_date}: {shop_error}")
                raise

            # Record the end time for logging
            end_time = datetime.now()
            elapsed_time = end_time - start_time
            logger.info(f"Completed fake data generation for {current_date} at {end_time} (Elapsed time: {elapsed_time})")

            return z
    except Exception as e:
        logger.critical(f"Critical error during fake data generation for {current_date}: {e}")
        return None

if __name__ == "__main__":
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 2).date()

    try:
        logger.info(f"Starting fake data generation from {start_date} to {end_date}")
        z = {}
        for i in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=i)
            asyncio.run(generate_fake_data(current_date, z))
        
        logger.info(f"Fake data generation completed successfully from {start_date} to {end_date}")
    except Exception as main_error:
        logger.critical(f"Critical error during main fake data generation process: {main_error}")
