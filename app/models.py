from sqlalchemy import Column, DateTime, JSON, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
import uuid
import enum
from datetime import datetime
import asyncio

Base = declarative_base()

class EventType(enum.Enum):
    user_account_creation = "user_account_creation"
    user_delete_account = "user_delete_account"
    user_shop_create = "user_shop_create"
    user_shop_delete = "user_shop_delete"
    user_deactivate_account = "user_deactivate_account"

class GlobalEvent(Base):
    __tablename__ = "global_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    event_metadata = Column(JSON, nullable=True)
    partition_key = Column(String, nullable=False)

    __table_args__ = {
        'postgresql_partition_by': 'LIST (partition_key)',
    }

    @staticmethod
    def generate_partition_key(event_time):
        return event_time.strftime("%Y-%m-%d:%H:00")
    


class EventPropensity:
    def __init__(
        self,
        max_fake_users_per_day=100,
        max_user_churn=0.1,
        max_first_shop_creation_percentage=0.8,
        max_multiple_shop_creation_percentage=0.1,
        max_shop_churn=0.2,
    ):

        self.max_fake_users_per_day = max_fake_users_per_day
        self.max_user_churn = max_user_churn
        self.max_first_shop_creation_percentage = max_first_shop_creation_percentage
        self.max_multiple_shop_creation_percentage = max_multiple_shop_creation_percentage
        self.max_shop_churn = max_shop_churn


class FakeHelper:
    def __init__(
        self,
        daily_users_created=0,
        daily_users_deactivated=0,
        daily_shops_created=0,
        daily_shops_deleted=0,
        semaphore=10,
        users=None,
        shops=None,
    ):

        self.daily_users_created = daily_users_created
        self.daily_users_deactivated = daily_users_deactivated
        self.daily_shops_created = daily_shops_created
        self.daily_shops_deleted = daily_shops_deleted

        self.users = users if users is not None else []
        self.shops = shops if shops is not None else []

        self.semaphore = asyncio.Semaphore(semaphore)