from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class Shop(Base, PartitionedModel):
    __tablename__ = 'shops'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_owner_id = Column(UUID(as_uuid=True), nullable=False)
    shop_name = Column(String(255), nullable=False)
    status = Column(Boolean, nullable=False, default=True)
    created_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deactivated_time = Column(DateTime(timezone=True))
    event_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = {'postgresql_partition_by': 'RANGE (partition_key)'}