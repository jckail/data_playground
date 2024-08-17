from .base import Base, PartitionedModel, generate_partition_name
from .user import User
from .shop import Shop
from .invoice import UserInvoice
from .payment import Payment
from .global_event import GlobalEvent, EventType
from .RequestResponseLog import RequestResponseLog
import asyncio
# Export all models
__all__ = [
    "Base", "PartitionedModel", "generate_partition_name",
    "User", "Shop", "UserInvoice", "Payment",
    "GlobalEvent", "EventType",
    "RequestResponseLog",
]


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

    def reset_daily_counts(self):
        """Resets the daily counts for users and shops."""
        self.daily_users_created = 0
        self.daily_users_deactivated = 0
        self.daily_shops_created = 0
        self.daily_shops_deleted = 0