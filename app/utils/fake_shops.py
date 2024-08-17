import asyncio
import httpx
from datetime import datetime, timedelta
import time

from ..models import EventPropensity, FakeHelper
from .helpers import (
    generate_event_time,
    process_tasks,
    post_request,
    BASE_URL,
    logger,
    fake,
    sampler
)

class Shop:
    def __init__(self, id, shop_owner_id, event_time=None, shop_name=None):
        self.id = id
        self.shop_owner_id = shop_owner_id
        self.event_time = event_time
        self.shop_name = shop_name

    async def delete_shop(self, client, current_date):
        try:
            self.deactive_time = await generate_event_time(
                current_date, self.event_time
            )
            payload = {"shop_id": self.id, "event_time": self.deactive_time}
            url = f"{BASE_URL}/delete_shop/"
            logger.info(f"Attempting to delete shop {self.id} at {self.deactive_time}")
            response = await post_request(
                client,
                url,
                payload,
                f"Failed to delete shop {self.id} at {self.deactive_time}",
            )
            logger.info(f"Successfully deleted shop {self.id} at {self.deactive_time}")
            return response
        except Exception as e:
            logger.error(f"Failed to delete shop {self.id}: {e}")
            return None

def shop_from_response(shops):
    if shops is None:
        logger.warning("No shops found in the response")
        return []

    valid_shops = []
    for shop in shops:
        try:
            valid_shops.append(
                Shop(
                    shop["event_metadata"]["shop_id"],
                    shop["event_metadata"]["shop_owner_id"],
                    shop["event_time"],
                    shop["event_metadata"].get("shop_name", None),  # Optional field
                )
            )
        except KeyError as e:
            logger.error(f"Missing key in shop data: {e}")
        except Exception as e:
            logger.error(f"Error creating Shop object: {e}")
    logger.info(f"Processed {len(valid_shops)} valid shops from response")
    return valid_shops

async def create_fake_shop(client, shop_owner_id, current_date):
    try:
        event_time = await generate_event_time(current_date)
        payload = {
            "shop_owner_id": shop_owner_id,
            "shop_name": fake.company(),
            "event_time": event_time,
        }
        url = f"{BASE_URL}/create_shop/"
        logger.info(f"Creating shop for user {shop_owner_id} at {event_time}")
        response = await post_request(
            client,
            url,
            payload,
            f"Failed to create shop for user {shop_owner_id} at {event_time}",
        )
        logger.info(f"Successfully created shop for user {shop_owner_id} at {event_time}")
        return response
    except Exception as e:
        logger.error(f"Error creating shop for user {shop_owner_id}: {e}")
        return None

async def generate_shops(client, current_date, user_list, propensity, exclusion=[]):
    user_list = [shop_owner_id for shop_owner_id in user_list if shop_owner_id not in exclusion]
    tasks = [
        create_fake_shop(client, shop_owner_id, current_date) for shop_owner_id in sampler(user_list, propensity, True)
    ]
    logger.info(f"Generating shops for {len(user_list)} users on {current_date}")
    return await process_tasks(client, tasks)

async def handle_shops(client, current_date, ep, fh: FakeHelper):
    try:
        logger.info(f"Handling shops for {current_date}")

        active_users = [user.id for user in fh.users]  # Get the IDs of the active users
        existing_shop_owners = [shop.shop_owner_id for shop in fh.shops]

        todays_first_shops = await generate_shops(
            client,
            current_date,
            active_users,
            ep.max_first_shop_creation_percentage,
            existing_shop_owners,
        )
        fh.shops.extend(shop_from_response(todays_first_shops))

        existing_shop_owners = [shop.shop_owner_id for shop in fh.shops]
        todays_next_shops = await generate_shops(
            client,
            current_date,
            existing_shop_owners,
            ep.max_multiple_shop_creation_percentage,
        )
        fh.shops.extend(shop_from_response(todays_next_shops))

        fh.daily_shops_created = len(todays_next_shops) + len(todays_first_shops)
        logger.info(f"{fh.daily_shops_created} shops created on {current_date}")

        del_user_shops = [shop for shop in fh.shops if shop.shop_owner_id not in active_users]
        del_queue = del_user_shops + sampler(fh.shops, ep.max_shop_churn, True)

        tasks = [shop.delete_shop(client, current_date) for shop in del_queue]
        todays_deletions = await process_tasks(client, tasks)
        td = shop_from_response(todays_deletions)
        fh.daily_shops_deleted = len(td)

        fh.shops = [shop for shop in fh.shops if shop.id not in [dshop.id for dshop in td]]
        logger.info(f"{fh.daily_shops_deleted} shops deleted on {current_date}")

        return fh
    except Exception as e:
        logger.error(f"Error handling shops for date {current_date}: {e}")
        return fh

if __name__ == "__main__":
    from .fake_users import handle_users
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 8).date()

    async def generate_fake_shop_data(start_date, end_date, ep: EventPropensity = EventPropensity(), semaphore=10):
        try:
            start_time = time.time()
            logger.info(f"Starting fake shop data generation from {start_date} to {end_date}")

            async with httpx.AsyncClient() as client:
                z = {}
                fh = FakeHelper(semaphore=semaphore)

                for i in range((end_date - start_date).days + 1):
                    current_date = start_date + timedelta(days=i)
                    logger.info(f"Generating fake data for {current_date}")
                    z[current_date] = await handle_users(client, current_date, ep, fh)
                    z[current_date] = await handle_shops(client, current_date, ep, z[current_date])

                end_time = time.time()
                run_time = end_time - start_time

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
                    "run_time": round(run_time, 4),
                }

                logger.info(f"Fake shop data generation completed with summary: {summary_dict}")
                return summary_dict
        except Exception as e:
            logger.critical(f"Critical error during fake shop data generation: {e}")
            return {}

    asyncio.run(generate_fake_shop_data(start_date, end_date))
