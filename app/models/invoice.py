from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, Float, Date, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class UserInvoice(Base, PartitionedModel):
    __tablename__ = 'user_invoices'

    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    shop_id = Column(UUID(as_uuid=True), nullable=False)
    invoice_amount = Column(Float, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())

    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id', 'partition_key'],
            ['users.id', 'users.partition_key']
        ),
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['shops.id', 'shops.partition_key']
        ),
        {'postgresql_partition_by': 'RANGE (partition_key)'},
    )