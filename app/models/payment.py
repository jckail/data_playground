from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, Float, ForeignKey, Date, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

class Payment(Base, PartitionedModel):
    __tablename__ = 'payments'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), nullable=False)
    payment_amount = Column(Float, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = {'postgresql_partition_by': 'RANGE (partition_key)'}
