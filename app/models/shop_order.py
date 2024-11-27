from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, Float, UUID, Index
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
import enum

class OrderStatus(enum.Enum):
    """Possible states for an order"""
    PENDING = "pending"  # Order created but not processed
    PROCESSING = "processing"  # Order being prepared
    SHIPPED = "shipped"  # Order sent to customer
    DELIVERED = "delivered"  # Order received by customer
    CANCELLED = "cancelled"  # Order cancelled before completion
    REFUNDED = "refunded"  # Order refunded after completion
    ON_HOLD = "on_hold"  # Order temporarily suspended
    RETURNED = "returned"  # Order returned by customer

class ShippingMethod(enum.Enum):
    """Available shipping methods"""
    STANDARD = "standard"  # Regular shipping (3-5 days)
    EXPRESS = "express"  # Expedited shipping (1-2 days)
    OVERNIGHT = "overnight"  # Next-day delivery
    LOCAL_PICKUP = "local_pickup"  # Customer picks up from store
    INTERNATIONAL = "international"  # International shipping

class FakeUserShopOrder(Base, PartitionedModel):
    """
    Represents an order placed by a user at a shop. Orders contain items,
    handle payments, and track shipping status. They can also receive reviews
    and be part of promotions.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - order_number is indexed for quick order lookups
    - status is indexed for filtering orders by status
    - fake_user_id is indexed for customer-based queries
    - fake_user_shop_id is indexed for shop-based queries
    - ordered_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - shipping_method is indexed for shipping-based queries
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'fake_user_shop_orders'
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
        unique=True,
        index=True,  # Added index
        comment="Human-readable order reference number"
    )
    fake_user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the user who placed the order"
    )
    fake_user_shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the shop where the order was placed"
    )
    
    # Order Status
    status = Column(
        Enum(OrderStatus), 
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
        Enum(ShippingMethod), 
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
        index=True,
        comment="Key used for time-based table partitioning"
    )

    # Relationships
    # Items included in this order
    items = relationship(
        "FakeUserShopOrderItem",
        backref=backref("order", lazy="joined"),
        foreign_keys="FakeUserShopOrderItem.order_id",
        lazy="dynamic"
    )
    
    # Payments made for this order
    payments = relationship(
        "FakeUserShopOrderPayment",
        backref=backref("order", lazy="joined"),
        foreign_keys="FakeUserShopOrderPayment.order_id",
        lazy="dynamic"
    )
    
    # Reviews for this order
    reviews = relationship(
        "FakeUserShopReview",
        backref=backref("order", lazy="joined"),
        foreign_keys="FakeUserShopReview.order_id",
        lazy="dynamic"
    )
    
    # Promotions used on this order
    promotion_usages = relationship(
        "FakeUserShopPromotionUsage",
        backref=backref("order", lazy="joined"),
        foreign_keys="FakeUserShopPromotionUsage.order_id",
        lazy="dynamic"
    )
    
    # Inventory changes related to this order
    inventory_logs = relationship(
        "FakeUserShopInventoryLog",
        backref=backref("order", lazy="joined"),
        foreign_keys="FakeUserShopInventoryLog.order_id",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        # Composite index for shop and status for filtering orders by status within a shop
        Index('ix_fake_user_shop_orders_shop_status', 'fake_user_shop_id', 'status'),
        
        # Composite index for user and status for filtering user's orders by status
        Index('ix_fake_user_shop_orders_user_status', 'fake_user_id', 'status'),
        
        # Composite index for shop and ordered_time for time-based queries within a shop
        Index('ix_fake_user_shop_orders_shop_ordered', 'fake_user_shop_id', 'ordered_time'),
        
        # Composite index for user and ordered_time for user's order history
        Index('ix_fake_user_shop_orders_user_ordered', 'fake_user_id', 'ordered_time'),
        
        # Composite index for shipping-related queries
        Index('ix_fake_user_shop_orders_shipping', 'shipping_method', 'shipping_country', 'shipping_state'),
        
        # Foreign key constraints
        ForeignKeyConstraint(
            ['fake_user_id'], ['data_playground.fake_users.id'],
            name='fk_fake_user_shop_order_user',
            comment="Foreign key relationship to the fake_users table"
        ),
        ForeignKeyConstraint(
            ['fake_user_shop_id'], ['data_playground.fake_user_shops.id'],
            name='fk_fake_user_shop_order_shop',
            comment="Foreign key relationship to the fake_user_shops table"
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
        from .shop_order_item import FakeUserShopOrderItem
        item = await FakeUserShopOrderItem.create_with_partition(
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
    async def add_payment(self, db, payment_method_id, amount, **payment_data):
        """Add a payment to the order"""
        from .payment_method import FakeUserShopOrderPayment
        payment = await FakeUserShopOrderPayment.create_with_partition(
            db,
            order_id=self.id,
            payment_method_id=payment_method_id,
            amount=amount,
            **payment_data
        )
        return payment

    async def get_payments(self, db):
        """Get all payments for the order"""
        return await self.payments.all()

    async def get_total_paid(self, db):
        """Calculate total amount paid"""
        payments = await self.payments.all()
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
        from .shop_review import FakeUserShopReview
        review = await FakeUserShopReview.create_with_partition(
            db,
            order_id=self.id,
            fake_user_id=self.fake_user_id,
            fake_user_shop_id=self.fake_user_shop_id,
            **review_data
        )
        return review

    async def get_reviews(self, db):
        """Get all reviews for the order"""
        return await self.reviews.all()

class FakeUserShopOrderItem(Base, PartitionedModel):
    """
    Represents an individual item within an order, including quantity,
    pricing, and status information.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - order_id is indexed for order-based queries
    - product_id is indexed for product-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    """
    __tablename__ = 'fake_user_shop_order_items'
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
        index=True,
        comment="Key used for time-based table partitioning"
    )

    # Indexes for common queries
    __table_args__ = (
        # Composite index for order items by price
        Index('ix_fake_user_shop_order_items_order_price', 'order_id', 'unit_price'),
        
        # Composite index for order items by quantity
        Index('ix_fake_user_shop_order_items_order_quantity', 'order_id', 'quantity'),
        
        # Composite index for cancelled/refunded items
        Index('ix_fake_user_shop_order_items_status', 'is_cancelled', 'is_refunded'),
        
        # Foreign key constraints
        ForeignKeyConstraint(
            ['order_id'], ['data_playground.fake_user_shop_orders.id'],
            name='fk_fake_user_shop_order_item_order',
            comment="Foreign key relationship to the fake_user_shop_orders table"
        ),
        ForeignKeyConstraint(
            ['product_id'], ['data_playground.fake_user_shop_products.id'],
            name='fk_fake_user_shop_order_item_product',
            comment="Foreign key relationship to the fake_user_shop_products table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores order item data with hourly partitioning for efficient querying'
        }
    )
