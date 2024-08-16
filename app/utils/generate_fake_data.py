import asyncio
import httpx
from datetime import datetime, timedelta

from ..models import EventPropensity, FakeHelper


from .helpers import (

    logger,
)
from .fake_users import handle_users
from .fake_shops import handle_shops


async def generate_fake_data(
    current_date,
    z : dict,
    ep: EventPropensity = EventPropensity(),
    fh: FakeHelper = FakeHelper()
):
    try:
        # Record the start time
        
        
        async with httpx.AsyncClient() as client:

            z[current_date] = await handle_users(
                client,
                current_date,
                ep,
                fh,
            )

            z[current_date] = await handle_shops(
                client, current_date, ep, z[current_date]
            )

            return z
    except Exception as e:
        logger.error(f"Error during fake shop data generation: {e}")
        return None


if __name__ == "__main__":
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 2).date()

    asyncio.run(generate_fake_data(start_date, end_date))


