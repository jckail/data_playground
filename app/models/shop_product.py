from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, JSON, Enum, Float, Integer, UUID, Index
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
import enum

class ProductCategory(enum.Enum):
    """Categories available for products"""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    FOOD = "food"
    BOOKS = "books"
    HOME = "home"
    BEAUTY = "beauty"
    SPORTS = "sports"
    TOYS = "toys"
    AUTOMOTIVE = "automotive"
    HEALTH = "health"
    OTHER = "other"

class ProductStatus(enum.Enum):
    """Possible states for a product"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"

class FakeUserShopProduct(Base, PartitionedModel):
    """
    Represents a product offered by a shop. Products can be ordered,
    reviewed, and tracked in inventory. They also maintain their own metrics.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - sku is indexed for quick product lookups
    - category is indexed for category-based filtering
    - status is indexed for filtering active/inactive products
    - price is indexed for price-based filtering and sorting
    - stock_quantity is indexed for inventory queries
    - fake_user_shop_id is indexed for shop-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'fake_user_shop_products'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the product"
    )
    fake_user_shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the shop that owns this product"
    )
    
    # Product Details
    sku = Column(
        String(50), 
        nullable=False,
        index=True,  # Added index
        comment="Stock Keeping Unit - unique product identifier within the shop"
    )
    name = Column(
        String(255), 
        nullable=False,
        index=True,  # Added index for product search
        comment="Display name of the product"
    )
    description = Column(
        String(1000), 
        nullable=True,
        comment="Detailed description of the product"
    )
    category = Column(
        Enum(ProductCategory), 
        nullable=False, 
        default=ProductCategory.OTHER,
        index=True,  # Added index
        comment="Category the product belongs to"
    )
    status = Column(
        Enum(ProductStatus), 
        nullable=False, 
        default=ProductStatus.ACTIVE,
        index=True,  # Added index
        comment="Current status of the product"
    )
    
    # Pricing and Inventory
    price = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Regular selling price"
    )
    sale_price = Column(
        Float, 
        nullable=True,
        index=True,  # Added index
        comment="Discounted price (if on sale)"
    )
    cost_price = Column(
        Float, 
        nullable=True,
        comment="Cost to acquire or produce the product"
    )
    stock_quantity = Column(
        Integer, 
        nullable=False, 
        default=0,
        index=True,  # Added index
        comment="Current quantity in stock"
    )
    low_stock_threshold = Column(
        Integer, 
        nullable=True,
        comment="Quantity at which to trigger low stock alerts"
    )
    
    # Product Specifications
    weight = Column(
        Float, 
        nullable=True,
        comment="Weight in grams"
    )
    dimensions = Column(
        String(50), 
        nullable=True,
        comment="Dimensions in format LxWxH (cm)"
    )
    manufacturer = Column(
        String(255), 
        nullable=True,
        index=True,  # Added index
        comment="Name of the manufacturer"
    )
    brand = Column(
        String(255), 
        nullable=True,
        index=True,  # Added index
        comment="Brand name of the product"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the product was created"
    )
    updated_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="Last time the product was updated"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    tags = Column(
        JSON, 
        nullable=True, 
        default=[],
        comment="Array of searchable tags"
    )
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional product data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False, 
        index=True,
        comment="Key used for time-based table partitioning"
    )

    # Relationships
    # Order items containing this product
    order_items = relationship(
        "FakeUserShopOrderItem",
        backref=backref("product", lazy="joined"),
        foreign_keys="FakeUserShopOrderItem.product_id",
        lazy="dynamic"
    )
    
    # Reviews for this product
    reviews = relationship(
        "FakeUserShopReview",
        backref=backref("product", lazy="joined"),
        foreign_keys="FakeUserShopReview.product_id",
        lazy="dynamic"
    )
    
    # Inventory change logs for this product
    inventory_logs = relationship(
        "FakeUserShopInventoryLog",
        backref=backref("product", lazy="joined"),
        foreign_keys="FakeUserShopInventoryLog.product_id",
        lazy="dynamic"
    )
    
    # Hourly metrics for this product
    hourly_metrics = relationship(
        "FakeUserShopProductMetricsHourly",
        backref=backref("product", lazy="joined"),
        foreign_keys="FakeUserShopProductMetricsHourly.product_id",
        lazy="dynamic"
    )
    
    # Daily metrics for this product
    daily_metrics = relationship(
        "FakeUserShopProductMetricsDaily",
        backref=backref("product", lazy="joined"),
        foreign_keys="FakeUserShopProductMetricsDaily.product_id",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        # Composite index for shop and status for filtering active products by shop
        Index('ix_fake_user_shop_products_shop_status', 'fake_user_shop_id', 'status'),
        
        # Composite index for shop and category for filtering products by category within a shop
        Index('ix_fake_user_shop_products_shop_category', 'fake_user_shop_id', 'category'),
        
        # Composite index for price range queries within a shop
        Index('ix_fake_user_shop_products_shop_price', 'fake_user_shop_id', 'price'),
        
        # Composite index for inventory management
        Index('ix_fake_user_shop_products_shop_stock', 'fake_user_shop_id', 'stock_quantity'),
        
        # Composite index for product search by name within a shop
        Index('ix_fake_user_shop_products_shop_name', 'fake_user_shop_id', 'name'),
        
        # Foreign key constraint
        ForeignKeyConstraint(
            ['fake_user_shop_id'], ['data_playground.fake_user_shops.id'],
            name='fk_fake_user_shop_product_shop',
            comment="Foreign key relationship to the fake_user_shops table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores product data with hourly partitioning for efficient querying'
        }
    )

    # Helper Methods for Inventory Operations
    async def update_stock(self, db, quantity_change, change_type, **log_data):
        """Update stock quantity and log the change"""
        from .shop_inventory import FakeUserShopInventoryLog, InventoryChangeType
        
        # Record current quantity
        old_quantity = self.stock_quantity
        
        # Update stock
        self.stock_quantity += quantity_change
        
        # Update status if needed
        if self.stock_quantity <= 0:
            self.status = ProductStatus.OUT_OF_STOCK
        elif self.status == ProductStatus.OUT_OF_STOCK and self.stock_quantity > 0:
            self.status = ProductStatus.ACTIVE
        
        # Create inventory log
        log = await FakeUserShopInventoryLog.create_with_partition(
            db,
            product_id=self.id,
            fake_user_shop_id=self.fake_user_shop_id,
            change_type=change_type,
            quantity_before=old_quantity,
            quantity_change=quantity_change,
            quantity_after=self.stock_quantity,
            **log_data
        )
        
        await db.commit()
        return log

    # Helper Methods for Review Operations
    async def get_reviews(self, db, status=None):
        """Get reviews for this product"""
        query = self.reviews
        if status:
            query = query.filter_by(status=status)
        return await query.all()

    async def get_average_rating(self, db):
        """Calculate average rating for this product"""
        reviews = await self.reviews.filter_by(status='APPROVED').all()
        if not reviews:
            return None
        return sum(review.rating for review in reviews) / len(reviews)

    # Helper Methods for Order Operations
    async def get_order_items(self, db, status=None):
        """Get order items for this product"""
        query = self.order_items
        if status:
            query = query.filter_by(status=status)
        return await query.all()

    # Helper Methods for Metrics
    async def get_metrics(self, db, timeframe='daily', start_time=None, end_time=None):
        """Get product metrics for a specific timeframe"""
        from .product_metrics import FakeUserShopProductMetricsDaily, FakeUserShopProductMetricsHourly
        MetricsModel = FakeUserShopProductMetricsDaily if timeframe == 'daily' else FakeUserShopProductMetricsHourly
        query = self.daily_metrics if timeframe == 'daily' else self.hourly_metrics
        if start_time:
            query = query.filter(MetricsModel.event_time >= start_time)
        if end_time:
            query = query.filter(MetricsModel.event_time <= end_time)
        return await query.all()
