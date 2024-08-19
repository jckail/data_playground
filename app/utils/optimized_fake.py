import asyncio
from datetime import datetime, timedelta, date
import uuid
import pytz
from typing import List, Dict
from faker import Faker
import logging
import httpx
import random
import os

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
    return datetime.utcnow().replace(tzinfo=pytz.UTC)

def generate_event_time(current_date: datetime) -> str:
    day_start = datetime.combine(current_date, datetime.min.time()).replace(tzinfo=pytz.UTC)
    day_end = datetime.combine(current_date, datetime.max.time()).replace(tzinfo=pytz.UTC)
    return fake.date_time_between(start_date=day_start, end_date=day_end, tzinfo=pytz.UTC).isoformat()

class Shop:
    def __init__(self, id, shop_owner_id, shop_name, event_time):
        self.id = id
        self.shop_owner_id = shop_owner_id
        self.created_time = event_time
        self.deactivated_time: None
        self.shop_name = shop_name

    def deactivate(self, event_time):
        self.deactivated_time = event_time

class User:
    def __init__(self,id, email, event_time):
        self.id = id
        self.email = email
        self.created_time = event_time
        self.deactivated_time = None
        self.shops = []
        
    def create_shop(self, shop_name, event_time):
        s =  Shop(self.id, shop_name, event_time)
        self.shops.append(s.id)
        return s
    
    def deactivate_shop(self, shop, event_time):
        for s in self.shops:
            if s.id == shop.id:
                shop.deactivate(event_time)
                return shop
        return None

    def deativate(self, event_time):
        for s in self.shops:
            s.deactivate()
        self.deactivated_time = event_time

# async def check_api_connection():
#     logger.info(f"Checking API connection to {BASE_URL}")
#     async with httpx.AsyncClient(timeout=10) as client:
#         try:
#             response = await client.get(BASE_URL)
#             logger.info(f"API check status: {response.status_code}")
#             return response.status_code == 200
#         except httpx.RequestError as e:
#             logger.error(f"Error connecting to API: {e}")
#             return False


# class odds_maker:
#     def __init__(self, 
#         max_fake_users_per_day=2000,
#         max_fake_shops_per_day=2000,

#         max_user_growth_rate=0.2,
#         max_shop_growth_rate=0.2,
#         user_shop_population=0.5,
#         shop_creation_chance=0.8,
        
#         user_churn_chance=0.2,
#         shop_churn_chance=0.3
        
        
#         ):

#         self.max_fake_users_per_day = max_fake_users_per_day
#         self.max_fake_shops_per_day = max_fake_shops_per_day
#         self.max_user_growth_rate = max_user_growth_rate
#         self.max_shop_growth_rate = max_shop_growth_rate
#         self.user_shop_population = user_shop_population
#         self.shop_creation_chance = shop_creation_chance
#         self.user_churn_chance = user_churn_chance
#         self.shop_churn_chance = shop_churn_chance
#         self.shops_to_generate = int(random.uniform(0, max_fake_shops_per_day)
#         )   

#     async def gen_prop(self, p_list, propensity, max_value=None, r=False):
#         population = len(p_list)
#         if population == 0:
#             return max_value

#         if not max_value:
#             max_value = population

#         if r:
#             propensity = random.uniform(0, propensity)

#         return min(int(len(population) * propensity), max_value)
    
#     async def list_randomizer(self, input_list):
#         for _ in range(int(random.uniform(1, 3))):
#             input_list = random.shuffle(input_list)
#         return input_list

#     async def generate_fake_user_growth_amount(self, user_list):
#         return await self.gen_prop(user_list, self.max_user_growth_rate, self.max_fake_users_per_day)
    
#     async def generate_fake_shop_growth(self, user_list, shop_list):
#         num_shops_to_create = await self.gen_prop(shop_list, self.max_shop_growth_rate, self.max_fake_shops_per_day)
#         user_list = self.list_randomizer(self, user_list)
#         return user_list[:num_shops_to_create]
    
#     async def generate_fake_shop_churn(self, shop_list):
#         num_shops_to_del = await self.gen_prop(shop_list, self.shop_churn_chance, self.max_fake_shops_per_day)
#         shop_list = self.list_randomizer(self, shop_list)
#         return shop_list[:num_shops_to_del]
    
#     async def generate_fake_shop_churn(self, shop_list):
#         num_shops_to_del = await self.gen_prop(shop_list, self.shop_churn_chance, self.max_fake_shops_per_day)
#         shop_list = self.list_randomizer(self, shop_list)
#         return shop_list[:num_shops_to_del]
    

# class action_counter:
#     def __init__(self):
#         self.users_created = 0
#         self.users_deactivated = 0
#         self.shops_created = 0
#         self.shops_deleted = 0

# class batch_data_store:
#     def __init__(self):
#         self.new_users = []
#         self.del_users = []
#         self.new_shops = []
#         self.del_shops = []
#         self.action_counter = action_counter()

#     async def update_action_counter(self):
#         self.action_counter.users_created = len(self.new_users)
#         self.action_counter.users_deactivated = len(self.del_users)
#         self.action_counter.shops_created = len(self.new_shops)
#         self.action_counter.shops_deleted = len(self.del_shops)

        
class base_data_store:
    """
    this is the main data store that will keep track of all users and shops
    it also keeps track of the daily data store
    # we want to queue everything IE generate to local THEN send to API
    # this will allow things to be updated before semaphore and async
    # should be generic
    # upon success of api Request save to base data store
    # create QUEUES 
    # from existing data --> generate odds --> generate lists and subsets --> process
    """
    def __init__(self,users = {}, shops = {}, action_counter = action_counter(), batch = batch_data_store()):
        self.users = users # {id: user}
        self.shops = shops # {id: shop}
        self.action_counter = action_counter
        self.batch = batch # {date: {users_created: 0, users_deactivated: 0, shops_created: 0, shops_deleted: 0}}

    async def post_batch_update(self):
        self.action_counter.users_created += len(self.batch.new_users)
        self.action_counter.users_deactivated += len(self.batch.del_users)
        self.action_counter.shops_created += len(self.batch.new_shops)
        self.action_counter.shops_deleted += len(self.batch.del_shops)
        self.batch = batch_data_store()

    async def create_user(self, email, event_time, client= None):
        id = None
        if client:
            url = f"{BASE_URL}/create_user/"
            payload = {"email": email, "event_time": event_time}
            response = await api_request(client, "POST", url, payload)
            if response:
                id = response["event_metadata"]["user_id"]

        if not id:
            id = uuid.uuid4()

        self.users[id] = User(id, email, event_time)

    async def create_shop(self,  user_id, shop_name, event_time, client = None):
        
        user = self.users[user_id]
        
        if event_time  > user.created_time and not user.deactivated_time:
            id = None

            if client:
                url = f"{BASE_URL}/create_shop/"
                payload = {"shop_owner_id": user.id, "shop_name": shop_name, "event_time": event_time}
                response = await api_request(client, "POST", url, payload)
                if response:
                    id = response["event_metadata"]["shop_id"]
                
            if not id:
                id = uuid.uuid4()

            s= user.create_shop(self, shop_name, event_time)
            self.shops[s.id] = s

    async def deactivate_shop(self,  shop_id, event_time, client = None):
        shop = self.shops[shop_id]
        if event_time  > shop.created_time:
        

            if client:
                url = f"{BASE_URL}/delete_shop/"
                payload = {"shop_id": shop.id, "event_time": event_time}
                await api_request(client, "POST", url, payload)

            shop.deactivate(event_time)


    async def deactivate_user(self, user_id, event_time, client= None):
        user = self.users[user_id]

        if event_time  > user.created_time:

            for shop_id in user.shops:
                await self.deactivate_shop(shop_id, event_time, client)
            
            if client:
                url = f"{BASE_URL}/deactivate_user/"
                payload = {"identifier": user.id, "event_time": event_time}
                await api_request(client, "POST", url, payload)

            user.deactivate(event_time)


# # use concept of "pool" or "avalible" to keep track of avalible users and shops an action can take place on
# # Only users without a deactivated_time can create or delete shops


#     async def create_fake_batch_user(self,current_date):
#         return fake.email(), generate_event_time(current_date)

#     async def create_fake_batch_user_queue(self, current_date):
#         for _ in range(100): #100 will be the generated value from the odds maker
#             email, event_time = await self.create_fake_batch_user(current_date)
#             self.batch.new_users.append((email, event_time))

#             # needs to return uncalled funciton and then arguments for it





# #     async def generate_fake_daily_shops(self, current_date, client = None):
# #         # percentage of users who will create shops:
# #         user_id = random.choice(list(self.users.keys()))

# #         # Odds a Selected User Will create a shop

# #         shop_name = fake.company()
# #         event_time = generate_event_time(current_date)
# #         await self.create_shop(user_id, shop_name, event_time, client)
        
        
        
        
# #         daily['users_created'] += 1


# #     def generate_fake_data(start_date, end_date):
# #         for i in range((end_date - start_date).days + 1):
# #             current_date = start_date + timedelta(days=i)
# #             self.daily[current_date] = daily_actions()
# #             for _ in range(self.max_fake_users_per_day):
# #         async with fh.semaphore:
# #         async with httpx.AsyncClient(timeout=60) as client:
# #             try:
# #                 fh = await handle_fake_data(client, current_date, ep, fh)
# #             except Exception as e:
# #                 logger.error(f"Error during fake data generation for {current_date}: {e}")
# #         Update Counts --> 
# #         settle daily then self.daily = daily_base_data_store()




# # fake.company()
# # fake.date_time_between(start_date=day_start, end_date=day_end, tzinfo=pytz.UTC).isoformat()
# # fake.email()

# # for _ in range(100):
# #     data_store().create_user(


async def check_api_connection(url):
    logger.info(f"Checking API connection to {url}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url)
            logger.info(f"API check status: {response.status_code}")
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.error(f"Error connecting to API: {e}")
            return False


async def create_fake_batch_user_queue(current_date):
    return User(uuid.uuid4(), fake.email(), generate_event_time(current_date))

async def generate_users_queue(n, current_date):
    tasks = [create_fake_batch_user_queue(current_date) for _ in range(n)]
    return await asyncio.gather(*tasks)

async def process_fake_batch_user_queue(url, user:User, client= None):
    if client:
        
        payload = {"email": user.email, "event_time": user.event_time}
        response = await api_request(client, "POST", url, payload)
        ## also add in  logic that if the request fails to return "None" and toss a log saying the user creation faild
        if response:
            user.id = response["event_metadata"]["user_id"]
    return user


async def generate_users( url, n , current_date, client = None):
    users = await generate_users_queue(n, current_date)
    if await check_api_connection(url):
        async with httpx.AsyncClient() as client:
                tasks = [process_fake_batch_user_queue(url, user, client) for user in users]
        return await asyncio.gather(*tasks)
    return users

async def main(user_dict):

    url = f"{BASE_URL}/create_user/"

    current_date = datetime.now()
    users = await generate_users(url, 10, current_date, client = None)
    for user in users:
        user_dict[user.id] = user
    
    print(user_dict)

if __name__ == "__main__":
    user_dict = {} # {id: user}
    asyncio.run(main(user_dict))