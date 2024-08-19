import asyncio
from datetime import datetime
import uuid
import pytz
from typing import List, Dict, Optional
from faker import Faker
import logging
import httpx
import os
from pydantic import BaseModel, Field

fake = Faker()

BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:8000')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def api_request(client: httpx.AsyncClient, method: str, url: str, payload: Dict = None, timeout: int = 30) -> Dict:
    try:
        response = await client.request(method, url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
    except httpx.RequestError as e:
        logger.error(f"Request error for {url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error for {url}: {e}")
    return None

def get_time():
    return datetime.now(pytz.UTC)

def generate_event_time(current_date: datetime) -> datetime:
    return fake.date_time_between_dates(
        datetime_start=current_date.replace(hour=0, minute=0, second=0, microsecond=0),
        datetime_end=current_date.replace(hour=23, minute=59, second=59, microsecond=999999),
        tzinfo=pytz.UTC
    )

async def check_api_connection(url: str) -> bool:
    health_check_url = f"{url.rstrip('/')}/health/"
    logger.info(f"Checking API connection to {health_check_url}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(health_check_url)
            logger.info(f"API check status: {response.status_code}")
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.error(f"Error connecting to API: {e}")
            return False


class Shop(BaseModel):
    id: uuid.UUID
    shop_owner_id: uuid.UUID
    shop_name: str
    created_time: datetime
    deactivated_time: Optional[datetime] = None

    def deactivate(self, event_time: datetime, client=None):
        self.deactivated_time = event_time

class User(BaseModel):
    id: uuid.UUID
    email: str
    created_time: datetime
    deactivated_time: Optional[datetime] = None
    shops: List[Shop] = Field(default_factory=list)

    async def call_create_user(self, client: httpx.AsyncClient):
        payload= {"email": self.email, "event_time": self.event_time.isoformat()}

        response = await api_request(client, "POST", f"{BASE_URL}/create_user/", payload)
        if response:
            self.id = uuid.UUID(response["event_metadata"]["user_id"])
            return self
        else:
            logger.error(f"User creation failed for email: {self.email}")
            return None

    def create_shop(self, shop_name: str, event_time: datetime, client=None) -> Shop:
        shop = Shop(
            id=uuid.uuid4(),
            shop_owner_id=self.id,
            shop_name=shop_name,
            created_time=event_time
        )
        self.shops.append(shop)
        return shop

    def deactivate_shop(self, shop: Shop, event_time: datetime, client=None) -> Optional[Shop]:
        for s in self.shops:
            if s.id == shop.id:
                s.deactivate(event_time)
                return s
        return None

    def deactivate(self, event_time: datetime, client=None):
        for shop in self.shops:
            shop.deactivate(event_time)
        self.deactivated_time = event_time


async def generate_fake_user(current_date: datetime) -> User:
    return User(
        id=uuid.uuid4(),
        email=fake.email(),
        created_time=generate_event_time(current_date)
    )



async def call_fake_user(url: str, user: User, client: httpx.AsyncClient) -> Optional[User]:
    payload = user.dict(include={'email', 'created_time'})
    payload['created_time'] = payload['created_time'].isoformat()  # Convert datetime to string
    response = await api_request(client, "POST", url, payload)
    if response:
        user.id = uuid.UUID(response["event_metadata"]["user_id"])
        return user
    else:
        logger.error(f"User creation failed for email: {user.email}")
        return None
    
    

async def generate_users(url: str, n: int, current_date: datetime) -> List[User]:
    users = await asyncio.gather(*[create_fake_user(current_date) for _ in range(n)])
    
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            processed_users = await asyncio.gather(*[process_fake_user(url, user, client) for user in users])
        return [user for user in processed_users if user is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed users.")
        return users

async def main(user_dict: Dict[uuid.UUID, User]):
    url = f"{BASE_URL}/create_user/"
    current_date = get_time()
    users = await generate_users(url, 10, current_date)
    
    for user in users:
        user_dict[user.id] = user
        # Example of using the new methods
        shop = user.create_shop(f"{user.email.split('@')[0]}'s Shop", current_date)
        logger.info(f"Created shop {shop.shop_name} for user {user.email}")
        
        # Deactivate the shop (for demonstration purposes)
        deactivated_shop = user.deactivate_shop(shop, current_date)
        if deactivated_shop:
            logger.info(f"Deactivated shop {deactivated_shop.shop_name}")
        
        # Deactivate the user (for demonstration purposes)
        user.deactivate(current_date)
        logger.info(f"Deactivated user {user.email}")
    
    logger.info(f"Generated {len(users)} users")
    logger.info(f"First 5 users: {[user.dict() for user in list(user_dict.values())[:5]]}")

if __name__ == "__main__":
    user_dict = {}
    asyncio.run(main(user_dict))


    """

    after taking a step back i think that sql model is a better paradigm
    1. entity mapping with relationship
    2. easier to query 
    3. easier to update
    4. easier to delete


    FLOW --> 
    1. Create User
    2. Given User creates shops
    3. Logs to "global_events" too for tracking


    1. Create User

    2. Inserts Record into User Table

    3. Inserts Record into Global Event Table
    

    """