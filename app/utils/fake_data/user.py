import asyncio
from datetime import datetime
import uuid
from typing import List,  Optional
from pydantic import BaseModel, Field
import httpx

from .new_fake_data_generator_helpers import (
    api_request,
    check_api_connection,
    generate_event_time,
    BASE_URL,
    logger,
    fake,
)

from .shop import Shop


#TODO: move this to actual app.models

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
            payload = {"identifier": str(self.id), "event_time": event_time.isoformat()}
            response = await api_request(
                client, "POST", f"{BASE_URL}/deactivate_user/", payload
            )
            if response:
                self.deactivated_time = event_time
                return self,shops
            else:
                logger.error(f"User Deletion failed for email: {self.email}")
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