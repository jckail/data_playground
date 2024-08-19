import asyncio
from datetime import datetime
import uuid
from typing import List, Dict, Optional
import httpx
from pydantic import BaseModel, Field


from .new_fake_data_generator_helpers import (
    BASE_URL,
    logger,
    check_api_connection

)

from .odds_maker import OddsMaker


from .user import User, Shop, generate_fake_user



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


