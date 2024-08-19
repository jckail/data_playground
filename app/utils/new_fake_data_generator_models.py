import asyncio
from datetime import datetime
import uuid
from typing import List, Dict, Optional
import httpx
from pydantic import BaseModel, Field
import random

from .new_fake_data_generator_helpers import (
    api_request,
    generate_event_time,
    BASE_URL,
    logger,
    fake,
    check_api_connection

)




class OddsMaker(BaseModel):
    max_fake_users_per_day: int = Field(default=2000)
    max_fake_shops_per_day: int = Field(default=2000)
    max_user_growth_rate: float = Field(default=0.2)
    max_shop_growth_rate: float = Field(default=0.2)
    user_shop_population: float = Field(default=0.5)
    shop_creation_chance: float = Field(default=0.8)
    user_churn_chance: float = Field(default=0.2)
    shop_churn_chance: float = Field(default=0.3)
    shops_to_generate: int = Field(default_factory=lambda: int(random.uniform(0, 2000)))

    async def gen_prop(self, p_list: List, propensity: float, max_value: int = None, r: bool = False) -> int:
        population = len(p_list)
        if population == 0:
            return max_value or 0

        if not max_value:
            max_value = population

        if r:
            propensity = random.uniform(0, propensity)

        return min(int(population * propensity), max_value)
    
    async def list_randomizer(self, input_list: List) -> List:
        for _ in range(int(random.uniform(1, 3))):
            random.shuffle(input_list)
        return input_list

    async def generate_fake_user_growth_amount(self, user_list: List) -> int:
        return await self.gen_prop(user_list, self.max_user_growth_rate, self.max_fake_users_per_day)
    
    async def generate_fake_shop_growth(self, user_list: List, shop_list: List) -> List:
        num_shops_to_create = await self.gen_prop(shop_list, self.max_shop_growth_rate, self.max_fake_shops_per_day)
        user_list = await self.list_randomizer(user_list)
        return user_list[:num_shops_to_create]
    
    async def generate_fake_shop_churn(self, shop_list: List) -> List:
        num_shops_to_del = await self.gen_prop(shop_list, self.shop_churn_chance, self.max_fake_shops_per_day)
        shop_list = await self.list_randomizer(shop_list)
        return shop_list[:num_shops_to_del]




class Shop(BaseModel):
    id: uuid.UUID
    shop_owner_id: uuid.UUID
    shop_name: str
    created_time: datetime
    deactivated_time: Optional[datetime] = None



    async def deactivate(self,current_date, event_time= None,   client=None):
        if not event_time:
            event_time = generate_event_time(current_date)
        if event_time > self.created_time and not self.deactivated_time:
            self.deactivated_time = event_time
            payload = {"shop_id": self.id, "event_time": self.deactivated_time}
            response = await api_request(
                client, "POST", f"{BASE_URL}/delete_shop/", payload
            )
            if response:
                return self
            else:
                logger.error(
                    f"Shop deletion failed for email: {self.shop_name}"
                )

                
            self.deactivated_time = event_time
            return self
        return None



class User(BaseModel):
    id: uuid.UUID
    email: str
    created_time: datetime
    deactivated_time: Optional[datetime] = None
    shops: List[uuid.UUID] = Field(default_factory=list)



    async def create_shop(self, current_date, client=None) -> Shop:

        shop = Shop(
                id=uuid.uuid4(),
                shop_owner_id=self.id,
                shop_name=fake.company(),
                created_time=generate_event_time(current_date),
            )

        if shop.created_time > self.created_time and not self.deactivated_time:
            payload = {
                "shop_owner_id": str(shop.shop_owner_id),
                "shop_name": shop.shop_name,
                "event_time": shop.created_time.isoformat(),
            }
            response = await api_request(
                client, "POST", f"{BASE_URL}/create_shop/", payload
            )
            if response:
                shop.id = uuid.UUID(response["event_metadata"]["shop_id"])
                self.shops.append(shop)
                return shop
            else:
                logger.error(
                    f"Shop creation failed for email: {shop.shop_name}"
                )
        return None

    #This should be a method considering create_shop is a method however the is simpler for now
    # def deactivate_shop(
    #     self, shop: Shop, current_date, client=None
    # ) -> Optional[Shop]:
    #     event_time = generate_event_time(current_date)
    #     if event_time > self.created_time and not self.deactivated_time:
    #         for s in self.shops:
    #             if s.id == shop.id:
    #                 s.deactivate(event_time,client)
    #                 return s
    #     return None

    async def deactivate(self,current_date, event_time= None,   client=None):
        if not event_time:
            event_time = generate_event_time(current_date)
        
        if event_time > self.created_time:
            shops = []
            for shop in self.shops:
                shops.append(await shop.deactivate(current_date, event_time, client))
            self.deactivated_time = event_time
            return self,shops
        return None, None

async def generate_fake_user(current_date: datetime, client: httpx.AsyncClient):

    user = User(
            id=uuid.uuid4(),
            email=fake.email(),
            created_time=generate_event_time(current_date),
        )

    payload = {
        "email": user.email,
        "event_time": user.created_time.isoformat(),
    }
    response = await api_request(
        client, "POST", f"{BASE_URL}/create_user/", payload
    )
    if response:
        user.id = uuid.UUID(response["event_metadata"]["user_id"])
        return user
    else:
        logger.error(f"User creation failed for email: {user.email}")
        return None


async def generate_users( n: int, current_date: datetime) -> List[User]:

    ###TODO:  CREATE BATCHES OF 1000 -- this number can be too high for the api
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            processed_users = await asyncio.gather(*[generate_fake_user( current_date, client)  for _ in range(n)])
        return [user for user in processed_users if user is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed users.")
        return None


async def generate_shops(users, n: int, current_date: datetime) -> List[User]:

    ###TODO:  CREATE BATCHES OF 1000 -- this number can be too high for the api
    # TODO since some event creation times are before the user creation time we need to reshuffle users and try to run generate shops again
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            processed_shops = await asyncio.gather(*[user.create_shop(current_date, client)  for user in users])
        return [shop for shop in processed_shops if shop is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed shops.")
        return None
    
async def deactivate_shops(shops, n: int, current_date: datetime) -> List[User]:
    ###TODO:  CREATE BATCHES OF 1000 -- this number can be too high for the api
    # TODO since some event creation times are before the user creation time we need to reshuffle users and try to run generate shops again
    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            processed_shops = await asyncio.gather(*[shop.deactivate(current_date, None, client)  for shop in shops])
        return [shop for shop in processed_shops if shop is not None]
    else:
        logger.warning("API connection failed. Returning unprocessed shops.")
        return None


async def deactivate_users(users, n: int, current_date: datetime) -> List[User]:
    ###TODO:  CREATE BATCHES OF 1000 -- this number can be too high for the api
    # TODO since some event creation times are before the user creation time we need to reshuffle users and try to run generate shops again
    r_users = []
    r_shops = []

    if await check_api_connection(BASE_URL):
        async with httpx.AsyncClient() as client:
            processed_users = await asyncio.gather(*[user.deactivate( current_date, None,  client)  for user in users])
            for user, shops in processed_users:
                if user is not None and shops is not None:
                    r_users.append(user)
                    r_shops += shops
            print('xxxxxx')
            return r_users, r_shops
                
    else:
        logger.warning("API connection failed. Returning unprocessed shops.")
        return None



class ActionCounter(BaseModel):
    users_created: int = 0
    users_deactivated: int = 0
    shops_created: int = 0
    shops_deleted: int = 0


class BatchDataStore(BaseModel):
    new_users: List[User] = Field(default_factory=list)
    del_users: List[User] = Field(default_factory=list)
    new_shops: List[Shop] = Field(default_factory=list)
    del_shops: List[Shop] = Field(default_factory=list)
    # with each new batch we will reset the action counter
    # and reset the instance of odds_maker
    active_users: List[Shop] = Field(default_factory=list)
    active_shops: List[Shop] = Field(default_factory=list)
    om : OddsMaker = Field(default_factory=OddsMaker) 

    



class BaseDataStore(BaseModel):
    active_users: Dict[uuid.UUID, User] = Field(default_factory=dict)
    active_shops: Dict[uuid.UUID, Shop] = Field(default_factory=dict)
    action_counter: ActionCounter = Field(default_factory=ActionCounter)
    all_bds: Dict = Field(default_factory=dict)
    bds: BatchDataStore = Field(default_factory=BatchDataStore) 

    def post_batch_update(self, current_date):
        self.action_counter.users_created += len(self.bds.new_users)
        self.action_counter.users_deactivated += len(self.bds.del_users)
        self.action_counter.shops_created += len(self.bds.new_shops)
        self.action_counter.shops_deleted += len(self.bds.del_shops)

        for user in self.bds.active_users:
            self.users[user.id] = user

        for shop in self.bds.active_shops:
            self.shop[shop.id] = shop

        self.all_bds[current_date] = self.bds


    def create_bds(self):
        self.bds = BatchDataStore()
        #self.bds.om = OddsMaker()
        self.bds.active_users = list(self.active_users.values())
        self.bds.active_shops = list(self.active_shops.values())
        print(self.bds.om.max_fake_shops_per_day)



        
    
    async def process_day(self,current_date):  #TODO replace main with a daily that takes in a datastore and a date
        #data_store = BaseDataStore() # this will be used accross days

        self.create_bds()
        self.bds.new_users = await generate_users( 1000, current_date)

        #TODO:  add in user shuffle logic here for which users generate shops
        new_shop_users = self.bds.new_users ##TODO: We will add in previously created users too! This will be a funciton on the base data store

        #todo this will run twice once for same day users
        # once for previous day users
        self.bds.new_shops = await generate_shops(new_shop_users, 1000, current_date)
        # TODO since some event creation times are before the user creation time we need to reshuffle users and try to run generate shops again
        
        
        within_deactivated_shops = await deactivate_shops(self.bds.new_shops, 1000, current_date)

        users_to_deactivate = self.bds.new_users
        deactivated_users, deactivated_shops = await deactivate_users(users_to_deactivate, 1000, current_date)


        daily_deactivated_shops =  within_deactivated_shops+ deactivated_shops

        self.bds.del_users = deactivated_users
        self.bds.del_shops = daily_deactivated_shops
        
        logger.info(f"Generated {len(self.bds.new_users)} users")
        logger.info(f"Generated {len(self.bds.new_shops)} shops")
        logger.info(f"Deactivated {len(within_deactivated_shops)} shops")
        logger.info(f"Deactivated {len(daily_deactivated_shops)} shops")
        logger.info(f"Deactivated {len(deactivated_users)} users")


        self.post_batch_update(current_date)

        #stopping point was at the main of the claude generated file 


