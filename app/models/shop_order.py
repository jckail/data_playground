from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, Float, UUID, Index, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
from .enums import OrderStatus, ShippingMethod, PaymentStatus

class ShopOrder(Base, PartitionedModel):
    """
    Represents an order placed by a user at a shop. Orders contain items,
    handle payments, and track shipping status. They can also receive reviews
    and be part of promotions.
    
    Indexing Strategy:
    - Primary key (id, partition_key) for partitioning support
    - order_number is indexed for quick order lookups
    - status is indexed for filtering orders by status
    - user_id is indexed for customer-based queries
    - shop_id is indexed for shop-based queries
    - ordered_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - shipping_method is indexed for shipping-based queries
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'shop_orders'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the order"
    )
    order_number = Column(
        String(50), 
        nullable=False,
        index=True,  # Added index
        comment="Human-readable order reference number"
    )
    user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the user who placed the order"
    )
    shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the shop where the order was placed"
    )
    
    # Order Status
    status = Column(
        Enum(OrderStatus, schema='data_playground'), 
        nullable=False, 
        default=OrderStatus.PENDING,
        index=True,  # Added index
        comment="Current status of the order"
    )
    
    # Financial Details
    subtotal = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Sum of all items before tax and shipping"
    )
    tax_amount = Column(
        Float, 
        nullable=True, 
        default=0.0,
        comment="Total tax charged"
    )
    shipping_amount = Column(
        Float, 
        nullable=True, 
        default=0.0,
        comment="Shipping cost"
    )
    discount_amount = Column(
        Float, 
        nullable=True, 
        default=0.0,
        comment="Total discounts applied"
    )
    total_amount = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Final order total including all charges and discounts"
    )
    
    # Shipping Details
    shipping_method = Column(
        Enum(ShippingMethod, schema='data_playground'), 
        nullable=True,
        index=True,  # Added index
        comment="Selected shipping method"
    )
    shipping_address_line1 = Column(
        String(255), 
        nullable=True,
        comment="Primary shipping address line"
    )
    shipping_address_line2 = Column(
        String(255), 
        nullable=True,
        comment="Secondary shipping address line"
    )
    shipping_city = Column(
        String(100), 
        nullable=True,
        index=True,  # Added index
        comment="City for shipping"
    )
    shipping_state = Column(
        String(100), 
        nullable=True,
        index=True,  # Added index
        comment="State/province for shipping"
    )
    shipping_postal_code = Column(
        String(20), 
        nullable=True,
        index=True,  # Added index
        comment="Postal/ZIP code for shipping"
    )
    shipping_country = Column(
        String(100), 
        nullable=True,
        index=True,  # Added index
        comment="Country for shipping"
    )
    
    # Tracking Information
    tracking_number = Column(
        String(100), 
        nullable=True,
        index=True,  # Added index
        comment="Shipping carrier tracking number"
    )
    tracking_url = Column(
        String(500), 
        nullable=True,
        comment="URL to track shipment"
    )
    
    # Timestamps
    ordered_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the order was placed"
    )
    processed_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        index=True,  # Added index
        comment="When the order started processing"
    )
    shipped_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        index=True,  # Added index
        comment="When the order was shipped"
    )
    delivered_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        index=True,  # Added index
        comment="When the order was delivered"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    notes = Column(
        String(1000), 
        nullable=True,
        comment="Order notes or special instructions"
    )
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional order data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    # Relationships
    # Items included in this order
    items = relationship(
        "ShopOrderItem",
        backref=backref("order", lazy="joined"),
        foreign_keys="ShopOrderItem.order_id",
        lazy="dynamic"
    )
    
    # Payments made for this order
    payments = relationship(
        "ShopOrderPayment",
        backref=backref("order", lazy="joined"),
        foreign_keys="ShopOrderPayment.order_id",
        lazy="dynamic"
    )
    
    # Reviews for this order
    reviews = relationship(
        "ShopReview",
        backref=backref("order", lazy="joined"),
        foreign_keys="ShopReview.order_id",
        lazy="dynamic"
    )
    
    # Promotions used on this order
    promotion_usages = relationship(
        "ShopPromotionUsage",
        backref=backref("order", lazy="joined"),
        foreign_keys="ShopPromotionUsage.order_id",
        lazy="dynamic"
    )
    
    # Inventory changes related to this order
    inventory_logs = relationship(
        "ShopInventoryLog",
        backref=backref("order", lazy="joined"),
        foreign_keys="ShopInventoryLog.order_id",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        # Unique constraint for order number must include partition key
        UniqueConstraint('order_number', 'partition_key', name='uq_shop_orders_number'),
        
        # Composite index for shop and status for filtering orders by status within a shop
        Index('ix_shop_orders_shop_status', 'shop_id', 'status'),
        
        # Composite index for user and status for filtering user's orders by status
        Index('ix_shop_orders_user_status', 'user_id', 'status'),
        
        # Composite index for shop and ordered_time for time-based queries within a shop
        Index('ix_shop_orders_shop_ordered', 'shop_id', 'ordered_time'),
        
        # Composite index for user and ordered_time for user's order history
        Index('ix_shop_orders_user_ordered', 'user_id', 'ordered_time'),
        
        # Composite index for shipping-related queries
        Index('ix_shop_orders_shipping', 'shipping_method', 'shipping_country', 'shipping_state'),
        
        # Foreign key constraints with partition key
        ForeignKeyConstraint(
            ['user_id', 'partition_key'],
            ['data_playground.users.id', 'data_playground.users.partition_key'],
            name='fk_shop_order_user',
            comment="Foreign key relationship to the users table"
        ),
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['data_playground.shops.id', 'data_playground.shops.partition_key'],
            name='fk_shop_order_shop',
            comment="Foreign key relationship to the shops table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores order data with hourly partitioning for efficient querying'
        }
    )

    # Helper Methods for Order Items
    async def add_item(self, db, product_id, quantity, unit_price, **item_data):
        """Add an item to the order"""
        from .shop_order_item import ShopOrderItem
        item = await ShopOrderItem.create_with_partition(
            db,
            order_id=self.id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=quantity * unit_price,
            **item_data
        )
        return item

    async def get_items(self, db):
        """Get all items in the order"""
        return await self.items.all()

    # Helper Methods for Payments
    async def record_payment(self, db, amount, payment_method, user_id, **payment_data):
        """Record a payment for this order"""
        from .ShopOrderPayments import ShopOrderPayment
        
        payment = await ShopOrderPayment.create_with_partition(
            db,
            order_id=self.id,
            user_id=user_id,
            shop_id=self.shop_id,
            amount=amount,
            method=payment_method,
            status=PaymentStatus.PENDING,
            **payment_data
        )
        
        # Update order status based on payment
        total_paid = sum(p.amount for p in await self.payments.filter_by(
            status=PaymentStatus.COMPLETED
        ).all())
        
        if total_paid + amount >= self.total_amount:
            await self.update_status(db, OrderStatus.PROCESSING)
        
        await db.commit()
        return payment

    async def get_payments(self, db):
        """Get all payments for the order"""
        return await self.payments.all()

    async def get_total_paid(self, db):
        """Calculate total amount paid"""
        payments = await self.payments.filter_by(status=PaymentStatus.COMPLETED).all()
        return sum(payment.amount for payment in payments)

    # Helper Methods for Status Updates
    async def update_status(self, db, new_status, **update_data):
        """Update order status and related fields"""
        self.status = new_status
        
        # Update timestamps based on status
        if new_status == OrderStatus.PROCESSING:
            self.processed_time = datetime.utcnow()
        elif new_status == OrderStatus.SHIPPED:
            self.shipped_time = datetime.utcnow()
        elif new_status == OrderStatus.DELIVERED:
            self.delivered_time = datetime.utcnow()
        
        # Update any additional fields
        for key, value in update_data.items():
            setattr(self, key, value)
        
        await db.commit()
        return self

    # Helper Methods for Inventory
    async def process_inventory(self, db, change_type):
        """Process inventory changes for all items"""
        from .shop_inventory import InventoryChangeType
        items = await self.items.all()
        for item in items:
            await item.product.update_stock(
                db,
                quantity_change=-item.quantity if change_type == InventoryChangeType.SALE else item.quantity,
                change_type=change_type,
                order_id=self.id
            )

    # Helper Methods for Reviews
    async def add_review(self, db, **review_data):
        """Add a review for the order"""
        from .shop_review import ShopReview
        review = await ShopReview.create_with_partition(
            db,
            order_id=self.id,
            user_id=self.user_id,
            shop_id=self.shop_id,
            **review_data
        )
        return review

    async def get_reviews(self, db):
        """Get all reviews for the order"""
        return await self.reviews.all()

class ShopOrderItem(Base, PartitionedModel):
    """
    Represents an individual item within an order, including quantity,
    pricing, and status information.
    
    Indexing Strategy:
    - Primary key (id, partition_key) for partitioning support
    - order_id is indexed for order-based queries
    - product_id is indexed for product-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    """
    __tablename__ = 'shop_order_items'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the order item"
    )
    order_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the parent order"
    )
    product_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the product ordered"
    )
    
    # Item Details
    quantity = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Quantity ordered"
    )
    unit_price = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Price per unit at time of order"
    )
    subtotal = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Total price before discounts (quantity * unit_price)"
    )
    discount_amount = Column(
        Float, 
        nullable=True, 
        default=0.0,
        comment="Discount applied to this item"
    )
    total_amount = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Final price after discounts"
    )
    
    # Status
    is_cancelled = Column(
        Boolean, 
        nullable=False, 
        default=False,
        index=True,  # Added index
        comment="Whether this item was cancelled"
    )
    is_refunded = Column(
        Boolean, 
        nullable=False, 
        default=False,
        index=True,  # Added index
        comment="Whether this item was refunded"
    )
    
    # Timestamps
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    notes = Column(
        String(1000), 
        nullable=True,
        comment="Notes specific to this item"
    )
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional item data stored as JSON"
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
        # Composite index for order items by price
        Index('ix_shop_order_items_order_price', 'order_id', 'unit_price'),
        
        # Composite index for order items by quantity
        Index('ix_shop_order_items_order_quantity', 'order_id', 'quantity'),
        
        # Composite index for cancelled/refunded items
        Index('ix_shop_order_items_status', 'is_cancelled', 'is_refunded'),
        
        # Foreign key constraints with partition key
        ForeignKeyConstraint(
            ['order_id', 'partition_key'],
            ['data_playground.shop_orders.id', 'data_playground.shop_orders.partition_key'],
            name='fk_shop_order_item_order',
            comment="Foreign key relationship to the shop_orders table"
        ),
        ForeignKeyConstraint(
            ['product_id', 'partition_key'],
            ['data_playground.shop_products.id', 'data_playground.shop_products.partition_key'],
            name='fk_shop_order_item_product',
            comment="Foreign key relationship to the shop_products table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores order item data with hourly partitioning for efficient querying'
        }
    )
