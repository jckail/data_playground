import asyncio
import httpx
from datetime import datetime, timedelta


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

import time


class Shop:
    def __init__(self, id, owner_id, event_time=None, shop_name=None):
        self.id = id
        self.owner_id = owner_id
        self.event_time = event_time
        self.shop_name = shop_name

    async def delete_shop(self, client, current_date):
        try:
            self.deactive_time = await generate_event_time(
                current_date, self.event_time
            )
            payload = {"shop_id": self.id, "event_time": self.deactive_time}
            url = f"{BASE_URL}/delete_shop/"
            return await post_request(
                client,
                url,
                payload,
                f"Failed to delete shop {self.id} at {self.deactive_time}",
            )
        except Exception as e:
            logger.error(f"Failed to delete shop {self.id}: {e}")
            return None


def shop_from_response(shops):
    if shops is None:
        return []

    valid_shops = []
    for shop in shops:
        try:
            valid_shops.append(
                Shop(
                    shop["event_metadata"]["shop_id"],
                    shop["event_metadata"]["user_id"],
                    shop["event_time"],
                    shop["event_metadata"].get(
                        "shop_name", None
                    ),  # Optional field
                )
            )
        except KeyError as e:
            logger.error(f"Missing key in shop data: {e}")
        except Exception as e:
            logger.error(f"Error creating Shop object: {e}")
    return valid_shops


async def create_fake_shop(client, user_id, current_date):
    try:
        event_time = await generate_event_time(current_date)
        payload = {
            "user_id": user_id,
            "shop_name": fake.company(),
            "event_time": event_time,
        }
        url = f"{BASE_URL}/create_shop/"
        return await post_request(
            client,
            url,
            payload,
            f"Failed to create shop for user {user_id} at {event_time}",
        )
    except Exception as e:
        logger.error(f"Error creating shop: {e}")
        return None


async def generate_shops(
    client, current_date, user_list, propensity, exclusion=[]
):

    user_list = [user_id for user_id in user_list if user_id not in exclusion]

    tasks = [
        create_fake_shop(client, user_id, current_date) for user_id in sampler(user_list, propensity,True)
    ]
    return await process_tasks(client, tasks)


async def handle_shops(client, current_date, ep, fh: FakeHelper):
    try:
        
        active_users = [
            user.id for user in fh.users
        ]  # Get the IDs of the active users

        existing_shop_owners = [shop.owner_id for shop in fh.shops]

        # cleanup_shops
        

        todays_first_shops = await generate_shops(
            client,
            current_date,
            active_users,
            ep.max_first_shop_creation_percentage,
            existing_shop_owners,
        )
        fh.shops.extend(shop_from_response(todays_first_shops))

        # Addtional Shops
        existing_shop_owners = [shop.owner_id for shop in fh.shops]
        todays_next_shops = await generate_shops(
            client,
            current_date,
            existing_shop_owners,
            ep.max_multiple_shop_creation_percentage,
        )
        fh.shops.extend(shop_from_response(todays_next_shops))

        # totals
        fh.daily_shops_created = (len(todays_next_shops) + len(
            todays_first_shops
        ))

        del_user_shops = [shop for shop in fh.shops if shop.owner_id not in active_users]
        

        del_queue = del_user_shops + sampler(fh.shops, ep.max_shop_churn,True)
    

        tasks = [shop.delete_shop(client, current_date) for shop in del_queue]

        todays_deletions = await process_tasks(client, tasks)
        td = shop_from_response(todays_deletions)
        fh.daily_shops_deleted = len(td)

        fh.shops = [
            shop
            for shop in fh.shops
            if shop.id not in [dshop.id for dshop in td]
        ]

        return fh
    except Exception as e:
        logger.error(f"Error handling shops for date {current_date}: {e}")
        return fh


if __name__ == "__main__":
    from .fake_users import handle_users
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 8).date()

    async def generate_fake_shop_data(
        start_date,
        end_date,
        ep: EventPropensity = EventPropensity(),
        semaphore=10,
    ):
        try:
            # Record the start time
            start_time = time.time()
            
            async with httpx.AsyncClient() as client:

                z = {}
                fh = FakeHelper(semaphore=semaphore)

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
            return {}

    asyncio.run(generate_fake_shop_data(start_date, end_date))
