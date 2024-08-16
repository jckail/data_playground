import asyncio
import httpx
from datetime import datetime, timedelta

from ..models import EventPropensity, FakeHelper


from .helpers import (

    logger,
)
from .fake_users import handle_users
from .fake_shops import handle_shops
import time


async def generate_fake_data(
    start_date,
    end_date,
    ep: EventPropensity = EventPropensity(),
    fh: FakeHelper = FakeHelper()
):
    try:
        # Record the start time
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:

            z = {}
            

            for i in range((end_date - start_date).days + 1):
                current_date = start_date + timedelta(days=i)
                z[current_date] = await handle_users(
                    client,
                    current_date,
                    ep,
                    fh,
                )

                z[current_date] = await handle_shops(
                    client, current_date, ep, z[current_date]
                )

            # Calculate the total runtime
            end_time = time.time()
            run_time = end_time - start_time

            logger.info(
                f"Fake shop data generation completed from {start_date} to {end_date}"
            )

            summary_dict = {
                "total_users_created": sum(z[current_date].daily_users_created for current_date in z),
                "total_users_deactivated": sum(z[current_date].daily_users_deactivated for current_date in z),
                "total_active_users": len(fh.users),
                "total_shops_created": sum(z[current_date].daily_shops_created for current_date in z),
                "total_shops_deleted": sum(z[current_date].daily_shops_deleted for current_date in z),
                "total_active_shops": len(fh.shops),
                "total_days": (end_date - start_date).days + 1,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "run_time": round(run_time,4),
            }

            print(summary_dict)
            return summary_dict
    except Exception as e:
        logger.error(f"Error during fake shop data generation: {e}")
        return None


if __name__ == "__main__":
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 2).date()

    asyncio.run(generate_fake_data(start_date, end_date))


