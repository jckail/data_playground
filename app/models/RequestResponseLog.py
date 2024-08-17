from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from .base import Base, PartitionedModel

class RequestResponseLog(Base, PartitionedModel):
    __tablename__ = 'request_response_logs'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    method = Column(String, index=True)
    url = Column(String, index=True)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    status_code = Column(Integer)
    event_time = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = {'postgresql_partition_by': 'LIST (partition_key)'}
