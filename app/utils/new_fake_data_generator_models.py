import asyncio
from datetime import datetime
import uuid
from typing import List, Dict, Optional
import httpx
from pydantic import BaseModel, Field

from .new_fake_data_generator_helpers import api_request,  generate_event_time, BASE_URL, logger, fake


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


class ActionCounter(BaseModel):
    users_created: int = 0
    users_deactivated: int = 0
    shops_created: int = 0
    shops_deleted: int = 0

class BatchDataStore(BaseModel):
    new_users_queue: List[User] = Field(default_factory=list)
    new_users: List[User] = Field(default_factory=list)
    del_users_queue: List[User] = Field(default_factory=list)
    del_users: List[User] = Field(default_factory=list)
    new_shops_queue: List[Shop] = Field(default_factory=list)
    new_shops: List[Shop] = Field(default_factory=list)
    del_shops_queue: List[Shop] = Field(default_factory=list)
    del_shops: List[Shop] = Field(default_factory=list)
    # with each new batch we will reset the action counter
    # and reset the instance of odds_maker

class BaseDataStore(BaseModel):
    users: Dict[uuid.UUID, User] = Field(default_factory=dict)
    shops: Dict[uuid.UUID, Shop] = Field(default_factory=dict)
    action_counter: ActionCounter = Field(default_factory=ActionCounter)
    batch: BatchDataStore = Field(default_factory=BatchDataStore)

    def post_batch_update(self):
        self.action_counter.users_created += len(self.batch.new_users)
        self.action_counter.users_deactivated += len(self.batch.del_users)
        self.action_counter.shops_created += len(self.batch.new_shops)
        self.action_counter.shops_deleted += len(self.batch.del_shops)
        self.batch = BatchDataStore()


    def update_base_data_store(self, users: List[User]):
        for user in users:
            self.users[user.id] = user
            self.batch.new_users.append(user)