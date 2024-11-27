from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, UUID, Index, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
import enum

class ShopCategory(enum.Enum):
    """Categories available for shops"""
    RETAIL = "retail"
    RESTAURANT = "restaurant"
    SERVICES = "services"
    TECHNOLOGY = "technology"
    FASHION = "fashion"
    HEALTH = "health"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"

class FakeUserShop(Base, PartitionedModel):
    """
    Represents a shop owned by a fake user. Shops can sell products,
    process orders, manage inventory, and handle customer interactions.
    
    Indexing Strategy:
    - Primary key (id, partition_key) for partitioning support
    - shop_category is indexed for filtering shops by category
    - status is indexed for filtering active/inactive shops
    - fake_user_owner_id is indexed for owner-based queries
    - created_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'fake_user_shops'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the shop"
    )
    fake_user_owner_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the user who owns this shop"
    )
    shop_name = Column(
        String(255), 
        nullable=False,
        index=True,  # Added index
        comment="Display name of the shop"
    )
    shop_description = Column(
        String(1000), 
        nullable=True,
        comment="Detailed description of the shop and its offerings"
    )
    shop_category = Column(
        Enum(ShopCategory), 
        nullable=False, 
        default=ShopCategory.OTHER,
        index=True,  # Added index
        comment="Primary category of the shop's business"
    )
    status = Column(
        Boolean, 
        nullable=False, 
        default=True,
        index=True,  # Added index
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
        index=True,  # Added index
        comment="City where the shop is located"
    )
    state = Column(
        String(100), 
        nullable=True,
        index=True,  # Added index
        comment="State/province where the shop is located"
    )
    postal_code = Column(
        String(20), 
        nullable=True,
        index=True,  # Added index
        comment="Postal/ZIP code"
    )
    country = Column(
        String(100), 
        nullable=True,
        index=True,  # Added index
        comment="Country where the shop is located"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the shop was created"
    )
    deactivated_time = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,  # Added index
        comment="When the shop was deactivated (if applicable)"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
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
        "FakeUserShopProduct",
        backref=backref("shop", lazy="joined"),
        foreign_keys="FakeUserShopProduct.fake_user_shop_id",
        lazy="dynamic"
    )
    
    # Orders placed at this shop
    orders = relationship(
        "FakeUserShopOrder",
        backref=backref("shop", lazy="joined"),
        foreign_keys="FakeUserShopOrder.fake_user_shop_id",
        lazy="dynamic"
    )
    
    # Reviews received by this shop
    reviews = relationship(
        "FakeUserShopReview",
        backref=backref("shop", lazy="joined"),
        foreign_keys="FakeUserShopReview.fake_user_shop_id",
        lazy="dynamic"
    )
    
    # Promotions offered by this shop
    promotions = relationship(
        "FakeUserShopPromotion",
        backref=backref("shop", lazy="joined"),
        foreign_keys="FakeUserShopPromotion.fake_user_shop_id",
        lazy="dynamic"
    )
    
    # Inventory change logs for this shop
    inventory_logs = relationship(
        "FakeUserShopInventoryLog",
        backref=backref("shop", lazy="joined"),
        foreign_keys="FakeUserShopInventoryLog.fake_user_shop_id",
        lazy="dynamic"
    )
    
    # Hourly metrics for this shop
    hourly_metrics = relationship(
        "FakeUserShopMetricsHourly",
        backref=backref("shop", lazy="joined"),
        foreign_keys="FakeUserShopMetricsHourly.fake_user_shop_id",
        lazy="dynamic"
    )
    
    # Daily metrics for this shop
    daily_metrics = relationship(
        "FakeUserShopMetricsDaily",
        backref=backref("shop", lazy="joined"),
        foreign_keys="FakeUserShopMetricsDaily.fake_user_shop_id",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        # Unique constraint for id and partition_key
        UniqueConstraint('id', 'partition_key', name='uq_fake_user_shops_id'),
        
        # Composite index for status and category for filtering active shops by category
        Index('ix_fake_user_shops_status_category', 'status', 'shop_category'),
        
        # Composite index for owner and status for filtering owner's active shops
        Index('ix_fake_user_shops_owner_status', 'fake_user_owner_id', 'status'),
        
        # Composite index for location-based queries
        Index('ix_fake_user_shops_location', 'country', 'state', 'city'),
        
        # Composite index for status and created_time for filtering active shops by creation date
        Index('ix_fake_user_shops_status_created', 'status', 'created_time'),
        
        # Foreign key constraint with partition key
        ForeignKeyConstraint(
            ['fake_user_owner_id', 'partition_key'],
            ['data_playground.fake_users.id', 'data_playground.fake_users.partition_key'],
            name='fk_fake_user_shop_owner',
            comment="Foreign key relationship to the fake_users table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores shop data with hourly partitioning for efficient querying'
        }
    )

    # Helper Methods for Product Operations
    async def add_product(self, db, **product_data):
        """Add a new product to the shop"""
        from .shop_product import FakeUserShopProduct
        product = await FakeUserShopProduct.create_with_partition(
            db, fake_user_shop_id=self.id, **product_data
        )
        return product

    async def get_products(self, db, active_only=True):
        """Get shop's products"""
        query = self.products
        if active_only:
            query = query.filter_by(status='ACTIVE')
        return await query.all()

    # Helper Methods for Order Operations
    async def get_orders(self, db, status=None):
        """Get orders for this shop"""
        query = self.orders
        if status:
            query = query.filter_by(status=status)
        return await query.all()

    async def process_order(self, db, order_id, new_status, **update_data):
        """Update order status and process accordingly"""
        order = await self.orders.filter_by(id=order_id).first()
        if order:
            order.status = new_status
            for key, value in update_data.items():
                setattr(order, key, value)
            await db.commit()
        return order

    # Helper Methods for Promotion Operations
    async def create_promotion(self, db, **promotion_data):
        """Create a new promotion for the shop"""
        from .shop_promotion import FakeUserShopPromotion
        promotion = await FakeUserShopPromotion.create_with_partition(
            db, fake_user_shop_id=self.id, **promotion_data
        )
        return promotion

    async def get_active_promotions(self, db):
        """Get active promotions for the shop"""
        return await self.promotions.filter_by(status='ACTIVE').all()

    # Helper Methods for Inventory Operations
    async def log_inventory_change(self, db, product_id, change_type, quantity_change, **log_data):
        """Log an inventory change"""
        from .shop_inventory import FakeUserShopInventoryLog
        log = await FakeUserShopInventoryLog.create_with_partition(
            db, 
            fake_user_shop_id=self.id,
            product_id=product_id,
            change_type=change_type,
            quantity_change=quantity_change,
            **log_data
        )
        return log

    # Helper Methods for Review Operations
    async def get_reviews(self, db, status=None):
        """Get reviews for this shop"""
        query = self.reviews
        if status:
            query = query.filter_by(status=status)
        return await query.all()

    # Helper Methods for Metrics
    async def get_metrics(self, db, timeframe='daily', start_time=None, end_time=None):
        """Get shop metrics for a specific timeframe"""
        from .shop_metrics import FakeUserShopMetricsDaily, FakeUserShopMetricsHourly
        MetricsModel = FakeUserShopMetricsDaily if timeframe == 'daily' else FakeUserShopMetricsHourly
        query = self.daily_metrics if timeframe == 'daily' else self.hourly_metrics
        if start_time:
            query = query.filter(MetricsModel.event_time >= start_time)
        if end_time:
            query = query.filter(MetricsModel.event_time <= end_time)
        return await query.all()
