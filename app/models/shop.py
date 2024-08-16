from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class Shop(Base, PartitionedModel):
    __tablename__ = 'shops'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_owner_id = Column(UUID(as_uuid=True), nullable=False)
    shop_name = Column(String(255), nullable=False)
    created_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deactivated_time = Column(DateTime(timezone=True))
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())

    __table_args__ = (
        ForeignKeyConstraint(
            ['shop_owner_id', 'partition_key'],
            ['users.id', 'users.partition_key']
        ),
        {'postgresql_partition_by': 'RANGE (partition_key)'},
    )