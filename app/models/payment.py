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
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())

    __table_args__ = (
        ForeignKeyConstraint(
            ['invoice_id', 'partition_key'],
            ['user_invoices.invoice_id', 'user_invoices.partition_key']
        ),
        {'postgresql_partition_by': 'RANGE (partition_key)'},
    )
