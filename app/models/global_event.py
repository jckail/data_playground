from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
import enum
from sqlalchemy.ext.hybrid import hybrid_property
from app.schemas import GlobalEventResponse


class EventType(enum.Enum):
    user_account_creation = "user_account_creation"
    user_delete_account = "user_delete_account"
    user_shop_create = "user_shop_create"
    user_shop_delete = "user_shop_delete"
    user_deactivate_account = "user_deactivate_account"

class GlobalEvent(Base, PartitionedModel):
    __tablename__ = "global_events"
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    event_metadata = Column(JSON, nullable=True)
    
    __table_args__ = {'postgresql_partition_by': 'LIST (partition_key)'}

    @hybrid_property
    def response(self):
        return GlobalEventResponse(
            event_id=str(self.event_id),
            event_time=self.event_time,
            event_type=self.event_type.value,
            event_metadata=self.event_metadata
        )
