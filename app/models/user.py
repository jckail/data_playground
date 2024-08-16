from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class User(Base, PartitionedModel):
    __tablename__ = 'users'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False)
    status = Column(Boolean, nullable=False, default=True)
    created_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deactivated_time = Column(DateTime(timezone=True))
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())
    
    __table_args__ = {'postgresql_partition_by': 'RANGE (partition_key)'}