import asyncio
from datetime import datetime
import uuid
from typing import List, Dict
from pydantic import BaseModel, Field


from .new_fake_data_generator_helpers import logger
from .odds_maker import OddsMaker
from .user import User, Shop
from .user_actions import generate_users, generate_shops, deactivate_shops, deactivate_users



class ActionCounter(BaseModel):
    users_created: int = 0
    users_deactivated: int = 0
    shops_created: int = 0
    shops_deleted: int = 0


class Batch(BaseModel):
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
    all_batch: Dict = Field(default_factory=dict)
    batch: Batch = Field(default_factory=Batch) 

    def post_batch_update(self, current_date):
        self.action_counter.users_created += len(self.batch.new_users)
        self.action_counter.users_deactivated += len(self.batch.del_users)
        self.action_counter.shops_created += len(self.batch.new_shops)
        self.action_counter.shops_deleted += len(self.batch.del_shops)

        for user in self.batch.active_users:
            self.users[user.id] = user

        for shop in self.batch.active_shops:
            self.shop[shop.id] = shop

        self.all_batch[current_date] = self.batch


    def create_batch(self):
        self.batch = Batch()
        #self.batch.om = OddsMaker()
        self.batch.active_users = list(self.active_users.values())
        self.batch.active_shops = list(self.active_shops.values())
        print(self.batch.om.max_fake_shops_per_day)
        
    
    async def process_day(self,current_date):  #TODO replace main with a daily that takes in a datastore and a date
        #data_store = BaseDataStore() # this will be used accross days

        self.create_batch()
        self.batch.new_users = await generate_users( 1000, current_date)

        #TODO:  add in user shuffle logic here for which users generate shops
        new_shop_users = self.batch.new_users ##TODO: We will add in previously created users too! This will be a funciton on the base data store

        #todo this will run twice once for same day users
        # once for previous day users
        self.batch.new_shops = await generate_shops(new_shop_users, 1000, current_date)
        # TODO since some event creation times are before the user creation time we need to reshuffle users and try to run generate shops again
        
        
        within_deactivated_shops = await deactivate_shops(self.batch.new_shops, 1000, current_date)

        users_to_deactivate = self.batch.new_users
        deactivated_users, deactivated_shops = await deactivate_users(users_to_deactivate, 1000, current_date)


        daily_deactivated_shops =  within_deactivated_shops+ deactivated_shops

        self.batch.del_users = deactivated_users
        self.batch.del_shops = daily_deactivated_shops
        
        logger.info(f"Generated {len(self.batch.new_users)} users")
        logger.info(f"Generated {len(self.batch.new_shops)} shops")
        logger.info(f"Deactivated {len(within_deactivated_shops)} shops")
        logger.info(f"Deactivated {len(daily_deactivated_shops)} shops")
        logger.info(f"Deactivated {len(deactivated_users)} users")


        self.post_batch_update(current_date)

        #stopping point was at the main of the claude generated file 


