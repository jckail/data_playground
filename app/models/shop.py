from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, UUID, Index, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
from .enums import ShopCategory

class Shop(Base, PartitionedModel):
    """
    Represents a shop owned by a user. Shops can sell products,
    process orders, manage inventory, and handle customer interactions.
    
    Indexing Strategy:
    - Primary key (id, partition_key) for partitioning support
    - shop_category is indexed for filtering shops by category
    - status is indexed for filtering active/inactive shops
    - owner_id is indexed for owner-based queries
    - created_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'shops'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the shop"
    )
    owner_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the user who owns this shop"
    )
    name = Column(
        String(255), 
        nullable=False,
        index=True,
        comment="Display name of the shop"
    )
    description = Column(
        String(1000), 
        nullable=True,
        comment="Detailed description of the shop and its offerings"
    )
    category = Column(
        Enum(ShopCategory, schema='data_playground'), 
        nullable=False, 
        default=ShopCategory.OTHER,
        index=True,
        comment="Primary category of the shop's business"
    )
    status = Column(
        Boolean, 
        nullable=False, 
        default=True,
        index=True,
        comment="Shop status (true=active, false=inactive)"
    )
    
    # Location Fields
    address_line1 = Column(
        String(255), 
        nullable=True,
        comment="Primary address line"
    )
    address_line2 = Column(
        String(255), 
        nullable=True,
        comment="Secondary address line (optional)"
    )
    city = Column(
        String(100), 
        nullable=True,
        index=True,
        comment="City where the shop is located"
    )
    state = Column(
        String(100), 
        nullable=True,
        index=True,
        comment="State/province where the shop is located"
    )
    postal_code = Column(
        String(20), 
        nullable=True,
        index=True,
        comment="Postal/ZIP code"
    )
    country = Column(
        String(100), 
        nullable=True,
        index=True,
        comment="Country where the shop is located"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,
        comment="When the shop was created"
    )
    deactivated_time = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="When the shop was deactivated (if applicable)"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional shop data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    # Relationships
    # Products offered by this shop
    products = relationship(
        "ShopProduct",
        backref=backref("shop", lazy="joined"),
        foreign_keys="ShopProduct.shop_id",
        lazy="dynamic"
    )
    
    # Orders placed at this shop
    orders = relationship(
        "ShopOrder",
        backref=backref("shop", lazy="joined"),
        foreign_keys="ShopOrder.shop_id",
        lazy="dynamic"
    )
    
    # Reviews received by this shop
    reviews = relationship(
        "ShopReview",
        backref=backref("shop", lazy="joined"),
        foreign_keys="ShopReview.shop_id",
        lazy="dynamic"
    )
    
    # Promotions offered by this shop
    promotions = relationship(
        "ShopPromotion",
        backref=backref("shop", lazy="joined"),
        foreign_keys="ShopPromotion.shop_id",
        lazy="dynamic"
    )
    
    # Inventory change logs for this shop
    inventory_logs = relationship(
        "ShopInventoryLog",
        backref=backref("shop", lazy="joined"),
        foreign_keys="ShopInventoryLog.shop_id",
        lazy="dynamic"
    )
    
    # Hourly metrics for this shop
    hourly_metrics = relationship(
        "ShopMetricsHourly",
        backref=backref("shop", lazy="joined"),
        foreign_keys="ShopMetricsHourly.shop_id",
        lazy="dynamic"
    )
    
    # Daily metrics for this shop
    daily_metrics = relationship(
        "ShopMetricsDaily",
        backref=backref("shop", lazy="joined"),
        foreign_keys="ShopMetricsDaily.shop_id",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        # Unique constraint for id and partition_key
        UniqueConstraint('id', 'partition_key', name='uq_shops_id'),
        
        # Composite index for status and category for filtering active shops by category
        Index('ix_shops_status_category', 'status', 'category'),
        
        # Composite index for owner and status for filtering owner's active shops
        Index('ix_shops_owner_status', 'owner_id', 'status'),
        
        # Composite index for location-based queries
        Index('ix_shops_location', 'country', 'state', 'city'),
        
        # Composite index for status and created_time for filtering active shops by creation date
        Index('ix_shops_status_created', 'status', 'created_time'),
        
        # Foreign key constraint with partition key
        ForeignKeyConstraint(
            ['owner_id', 'partition_key'],
            ['data_playground.users.id', 'data_playground.users.partition_key'],
            name='fk_shop_owner',
            comment="Foreign key relationship to the users table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores shop data with hourly partitioning for efficient querying'
        }
    )
