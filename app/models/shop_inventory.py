from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, JSON, Enum, Float, Integer, UUID, Index
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
from .enums import InventoryChangeType

class ShopInventoryLog(Base, PartitionedModel):
    """
    Tracks all inventory changes for products in a shop, including purchases,
    sales, returns, and adjustments. Provides a complete audit trail of
    stock movements and helps maintain accurate inventory levels.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - change_type is indexed for filtering by change types
    - shop_id is indexed for shop-based queries
    - product_id is indexed for product-based queries
    - order_id is indexed for order-based queries
    - created_by_user_id is indexed for user-based queries
    - created_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - quantity_before/after are indexed for stock level queries
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'shop_inventory_logs'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the inventory log entry"
    )
    shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the shop where the inventory change occurred"
    )
    product_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the product whose inventory changed"
    )
    order_id = Column(
        UUID(as_uuid=True), 
        nullable=True,
        index=True,
        comment="ID of the related order (if applicable)"
    )
    
    # Change Details
    change_type = Column(
        Enum(InventoryChangeType, schema='data_playground'), 
        nullable=False,
        index=True,
        comment="Type of inventory change that occurred"
    )
    quantity_before = Column(
        Integer, 
        nullable=False,
        index=True,
        comment="Stock quantity before the change"
    )
    quantity_change = Column(
        Integer, 
        nullable=False,
        index=True,
        comment="Amount of change (positive or negative)"
    )
    quantity_after = Column(
        Integer, 
        nullable=False,
        index=True,
        comment="Stock quantity after the change"
    )
    
    # Cost Tracking
    unit_cost = Column(
        Float, 
        nullable=True,
        index=True,
        comment="Cost per unit for this change"
    )
    total_cost = Column(
        Float, 
        nullable=True,
        index=True,
        comment="Total cost for this change"
    )
    
    # Reference Information
    reference_number = Column(
        String(100), 
        nullable=True,
        index=True,
        comment="External reference (PO number, return number, etc.)"
    )
    reason = Column(
        String(500), 
        nullable=True,
        comment="Explanation for the inventory change"
    )
    
    # User Tracking
    created_by_user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the user who made the change"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,
        comment="When the inventory change was recorded"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    notes = Column(
        String(1000), 
        nullable=True,
        comment="Additional notes about the change"
    )
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional inventory data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    # Indexes for common queries
    __table_args__ = (
        # Composite index for shop inventory changes by type
        Index('ix_shop_inventory_shop_type', 'shop_id', 'change_type'),
        
        # Composite index for product inventory changes by type
        Index('ix_shop_inventory_product_type', 'product_id', 'change_type'),
        
        # Composite index for order-related inventory changes
        Index('ix_shop_inventory_order', 'order_id', 'change_type'),
        
        # Composite index for user-initiated changes
        Index('ix_shop_inventory_user_time', 'created_by_user_id', 'created_time'),
        
        # Composite index for stock level tracking
        Index('ix_shop_inventory_levels', 'product_id', 'quantity_after', 'created_time'),
        
        # Foreign key constraints with partition key
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['data_playground.shops.id', 'data_playground.shops.partition_key'],
            name='fk_shop_inventory_log_shop',
            comment="Foreign key relationship to the shops table"
        ),
        ForeignKeyConstraint(
            ['product_id', 'partition_key'],
            ['data_playground.shop_products.id', 'data_playground.shop_products.partition_key'],
            name='fk_shop_inventory_log_product',
            comment="Foreign key relationship to the shop_products table"
        ),
        ForeignKeyConstraint(
            ['order_id', 'partition_key'],
            ['data_playground.shop_orders.id', 'data_playground.shop_orders.partition_key'],
            name='fk_shop_inventory_log_order',
            comment="Foreign key relationship to the shop_orders table"
        ),
        ForeignKeyConstraint(
            ['created_by_user_id', 'partition_key'],
            ['data_playground.users.id', 'data_playground.users.partition_key'],
            name='fk_shop_inventory_log_user',
            comment="Foreign key relationship to the users table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores inventory change logs with hourly partitioning for efficient querying'
        }
    )

    # Helper Methods for Analysis
    @classmethod
    async def get_product_history(cls, db, product_id, start_time=None, end_time=None):
        """Get inventory history for a specific product"""
        query = db.query(cls).filter(cls.product_id == product_id)
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        return await query.order_by(cls.event_time.desc()).all()

    @classmethod
    async def get_shop_history(cls, db, shop_id, start_time=None, end_time=None):
        """Get inventory history for a specific shop"""
        query = db.query(cls).filter(cls.shop_id == shop_id)
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        return await query.order_by(cls.event_time.desc()).all()

    @classmethod
    async def get_cost_analysis(cls, db, shop_id, start_time=None, end_time=None):
        """Get cost analysis for inventory changes"""
        query = db.query(cls).filter(
            cls.shop_id == shop_id,
            cls.unit_cost.isnot(None)
        )
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        
        logs = await query.all()
        return {
            'total_cost': sum(log.total_cost for log in logs if log.total_cost),
            'average_unit_cost': sum(log.unit_cost for log in logs if log.unit_cost) / len(logs) if logs else 0,
            'total_units_changed': sum(abs(log.quantity_change) for log in logs)
        }

    @classmethod
    async def get_movement_analysis(cls, db, shop_id, product_id=None, change_type=None):
        """Analyze inventory movement patterns"""
        query = db.query(cls).filter(cls.shop_id == shop_id)
        if product_id:
            query = query.filter(cls.product_id == product_id)
        if change_type:
            query = query.filter(cls.change_type == change_type)
        
        logs = await query.all()
        return {
            'total_movements': len(logs),
            'total_quantity_changed': sum(abs(log.quantity_change) for log in logs),
            'average_change_size': sum(abs(log.quantity_change) for log in logs) / len(logs) if logs else 0,
            'positive_changes': sum(1 for log in logs if log.quantity_change > 0),
            'negative_changes': sum(1 for log in logs if log.quantity_change < 0)
        }
