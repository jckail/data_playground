from sqlalchemy import Column, DateTime, JSON, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
import uuid
import enum
from datetime import datetime

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