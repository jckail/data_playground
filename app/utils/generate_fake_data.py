import asyncio
import httpx
from datetime import datetime, timedelta
import random
from faker import Faker
import pytz

BASE_URL = "http://localhost:8000"  # Adjust if your API is hosted elsewhere
fake = Faker()

async def create_user(client, email, event_time):
    response = await client.post(f"{BASE_URL}/create_user/", 
                                 json={"email": email, "event_time": event_time.isoformat()})
    response.raise_for_status()  # Raise an error for HTTP errors
    return response.json()

async def deactivate_user(client, identifier, event_time):
    response = await client.post(f"{BASE_URL}/deactivate_user/", 
                                 json={"identifier": identifier, "event_time": event_time.isoformat()})
    response.raise_for_status()
    return response.json()

async def create_shop(client, user_id, event_time):
    shop_name = fake.company()
    response = await client.post(f"{BASE_URL}/create_shop/", 
                                 json={"user_id": user_id, "shop_name": shop_name, "event_time": event_time.isoformat()})
    response.raise_for_status()
    return response.json()

async def delete_shop(client, shop_id, event_time):
    response = await client.post(f"{BASE_URL}/delete_shop/", 
                                 json={"shop_id": shop_id, "event_time": event_time.isoformat()})
    response.raise_for_status()
    return response.json()

async def generate_users_for_day(client, current_date):
    active_users = []
    active_shops = []
    total_users_created = 0
    total_users_deactivated = 0

    num_users_today = random.randint(10, 100)
    day_start = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=pytz.UTC)
    day_end = datetime.combine(current_date, datetime.max.time()).replace(tzinfo=pytz.UTC)

    tasks = []
    for _ in range(num_users_today):
        event_time = fake.date_time_between(start_date=day_start, end_date=day_end, tzinfo=pytz.UTC)
        email = fake.email()
        tasks.append(create_user(client, email, event_time))

    users = await asyncio.gather(*tasks)
    active_users.extend(user['event_metadata']['user_id'] for user in users)
    total_users_created += len(users)
    print(f"Created {len(users)} users on {current_date}")

    # Shop creation for users
    shop_creation_percentage = random.uniform(0.3, 0.9)
    num_users_creating_shops = int(len(active_users) * shop_creation_percentage)

    tasks = []
    for user_id in random.sample(active_users, num_users_creating_shops):
        # Each user may create a shop within 0 to 80 days of account creation
        shop_creation_time = fake.date_time_between(start_date=current_date, end_date=current_date + timedelta(days=80), tzinfo=pytz.UTC)
        tasks.append(create_shop(client, user_id, shop_creation_time))

    shops = await asyncio.gather(*tasks)
    active_shops.extend(shop['event_metadata']['shop_id'] for shop in shops)
    print(f"Created {len(shops)} shops on {current_date}")

    # Deactivate users
    num_users_to_deactivate = int(len(active_users) * random.uniform(0.01, 0.05))
    users_to_deactivate = random.sample(active_users, num_users_to_deactivate)

    tasks = []
    for user_id in users_to_deactivate:
        event_time = fake.date_time_between(start_date=day_start, end_date=day_end, tzinfo=pytz.UTC)
        tasks.append(deactivate_user(client, user_id, event_time))

    await asyncio.gather(*tasks)
    total_users_deactivated += len(users_to_deactivate)
    print(f"Deactivated {len(users_to_deactivate)} users on {current_date}")

    # Delete shops
    shop_deletion_percentage = random.uniform(0.01, 0.1)
    num_shops_to_delete = int(len(active_shops) * shop_deletion_percentage)

    tasks = []
    for shop_id in random.sample(active_shops, num_shops_to_delete):
        event_time = fake.date_time_between(start_date=day_start, end_date=day_end, tzinfo=pytz.UTC)
        tasks.append(delete_shop(client, shop_id, event_time))

    await asyncio.gather(*tasks)
    print(f"Deleted {len(num_shops_to_delete)} shops on {current_date}")

    print(f"Date: {current_date}, Users created: {total_users_created}, Users deactivated: {total_users_deactivated}, Shops created: {len(shops)}, Shops deleted: {num_shops_to_delete}")
    return total_users_created, total_users_deactivated, len(active_users), len(shops), num_shops_to_delete

async def generate_fake_data(start_date, end_date):
    async with httpx.AsyncClient() as client:
        current_date = start_date
        while current_date <= end_date:
            await generate_users_for_day(client, current_date)
            current_date += timedelta(days=1)

    print(f"Fake data generation completed from {start_date} to {end_date}")

if __name__ == "__main__":
    start_date = datetime(2023, 1, 1).date()
    end_date = datetime(2024, 8, 1).date()
    
    # Run the async function
    asyncio.run(generate_fake_data(start_date, end_date))
