import asyncio
import httpx
import random
from datetime import datetime, timedelta

from ..models import EventPropensity, FakeHelper
from .helpers import sampler, generate_event_time, process_tasks, post_request, BASE_URL, logger, fake

class User:
    def __init__(self, id, email=None, event_time=None):
        self.id = id
        self.email = email
        self.event_time = event_time

    async def deactivate_user(self, client, current_date):
        try:
            self.deactive_time = await generate_event_time(current_date, self.event_time)
            payload = {"identifier": self.id, "event_time": self.deactive_time}
            url = f"{BASE_URL}/deactivate_user/"
            logger.info(f"Deactivating user {self.id} at {self.deactive_time}")
            response = await post_request(
                client,
                url,
                payload,
                f"Failed to deactivate user {self.id} at {self.deactive_time}",
            )
            logger.info(f"Successfully deactivated user {self.id} at {self.deactive_time}")
            return response
        except Exception as e:
            logger.error(f"Failed to deactivate user {self.id}: {e}")
            return None

def user_from_response(users):
    if users is None:
        logger.warning("No users found in the response")
        return []

    valid_users = []
    for user in users:
        try:
            valid_users.append(
                User(
                    user["event_metadata"]["user_id"],
                    user["event_metadata"].get("email", None),  # Optional field
                    user["event_time"]
                )
            )
        except KeyError as e:
            logger.error(f"Missing key in user data: {e}")
        except Exception as e:
            logger.error(f"Error creating User object: {e}")
    logger.info(f"Processed {len(valid_users)} valid users from response")
    return valid_users

async def create_fake_user(client, current_date, fh: FakeHelper):
    try:
        email = fake.email()
        event_time = await generate_event_time(current_date)
        payload = {"email": email, "event_time": event_time}
        logger.info(f"Creating user with email {email} at {event_time}")
        response = await post_request(
            client,
            f"{BASE_URL}/create_user/",
            payload,
            f"Failed to create user {email} at {event_time}",
            fh.semaphore,
        )
        logger.info(f"Successfully created user with email {email} at {event_time}")
        return response
    except Exception as e:
        logger.error(f"Error creating user with email {email}: {e}")
        return None

async def handle_users(client, current_date, ep: EventPropensity, fh: FakeHelper):
    try:
        logger.info(f"Handling users for {current_date}")

        users_to_generate = int(random.uniform(0, ep.max_fake_users_per_day))
        logger.info(f"Generating {users_to_generate} users on {current_date}")

        tasks = [create_fake_user(client, current_date, fh) for _ in range(users_to_generate)]
        todays_users = await process_tasks(client, tasks)
        fh.daily_users_created = len(todays_users)
        logger.info(f"Created {fh.daily_users_created} users on {current_date}")

        fh.users.extend(user_from_response(todays_users))

        deactivate_queue = sampler(fh.users, ep.max_user_churn, True)
        logger.info(f"Deactivating {len(deactivate_queue)} users on {current_date}")

        tasks = [user.deactivate_user(client, current_date) for user in deactivate_queue]
        todays_deactivations = await process_tasks(client, tasks)

        td = user_from_response(todays_deactivations)
        fh.daily_users_deactivated = len(td)
        fh.users = [user for user in fh.users if user.id not in [ruser.id for ruser in td]]
        logger.info(f"Deactivated {fh.daily_users_deactivated} users on {current_date}")

        return fh
    except Exception as e:
        logger.error(f"Error handling users for date {current_date}: {e}")
        return fh

if __name__ == "__main__":
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 2).date()

    async def generate_fake_user_data(start_date, end_date, ep: EventPropensity = EventPropensity()):
        try:
            logger.info(f"Starting fake user data generation from {start_date} to {end_date}")
            async with httpx.AsyncClient() as client:
                total_users_created, total_users_deactivated = 0, 0
                z = {}
                fh = FakeHelper()

                for i in range((end_date - start_date).days + 1):
                    current_date = start_date + timedelta(days=i)
                    logger.info(f"Generating data for {current_date}")
                    z[current_date] = await handle_users(client, current_date, ep, fh)

                    total_users_created += z[current_date].daily_users_created
                    total_users_deactivated += z[current_date].daily_users_deactivated
                    total_active_users = len(z[current_date].users)

                logger.info(f"Fake user data generation completed. Total users created: {total_users_created}, "
                            f"Total users deactivated: {total_users_deactivated}, Total active users: {total_active_users}")
                return total_users_created, total_users_deactivated, total_active_users
        except Exception as e:
            logger.error(f"Error during fake data generation: {e}")
            return 0, 0, 0

    asyncio.run(generate_fake_user_data(start_date, end_date))
