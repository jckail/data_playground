from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, Enum, Index, UUID
import enum
from datetime import datetime

class EntityType(enum.Enum):
    FAKE_USER = "fake_user"
    FAKE_USER_SHOP = "fake_user_shop"
    FAKE_USER_SHOP_PRODUCT = "fake_user_shop_product"
    FAKE_USER_INVOICE = "fake_user_invoice"
    FAKE_USER_PAYMENT = "fake_user_payment"
    FAKE_USER_SHOP_ORDER = "fake_user_shop_order"
    FAKE_USER_SHOP_REVIEW = "fake_user_shop_review"
    FAKE_USER_SHOP_PROMOTION = "fake_user_shop_promotion"
    FAKE_USER_PAYMENT_METHOD = "fake_user_payment_method"

class GlobalEntity(Base, PartitionedModel):
    __tablename__ = 'global_entities'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    # Primary Fields
    event_time = Column(DateTime(timezone=True), primary_key=True)
    entity_id = Column(UUID(as_uuid=True), primary_key=True)
    partition_key = Column(String, primary_key=True)  # Added to primary key
    
    # Entity Type for table mapping
    entity_type = Column(Enum(EntityType), nullable=False)

    created_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deactivated_time = Column(DateTime(timezone=True))
    reactivated_time = Column(DateTime(timezone=True))

    __table_args__ = (
        # Index for looking up entities by type
        Index('idx_global_entity_type_time', 
              entity_type, event_time,
              postgresql_using='btree'),
        # Index for looking up entities by ID
        Index('idx_global_entity_id_type', 
              entity_id, entity_type,
              postgresql_using='btree'),
        # Index for time-based queries
        Index('idx_global_entity_time_id', 
              event_time, entity_id,
              postgresql_using='btree'),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )
