from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, Float, Integer, UUID, ARRAY, Index, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
from .enums import PromotionType, PromotionStatus, PromotionApplicability

class ShopPromotion(Base, PartitionedModel):
    """
    Represents a promotional offer created by a shop. Promotions can offer
    various types of discounts and can be limited by time, usage, or
    specific products/categories.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - promotion_type is indexed for filtering by promotion types
    - status is indexed for filtering active/inactive promotions
    - shop_id is indexed for shop-based queries
    - valid_from/until are indexed for time-based queries
    - promo_code is indexed for code lookups
    - applicability is indexed for filtering by applicability
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'shop_promotions'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the promotion"
    )
    shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the shop offering the promotion"
    )
    
    # Promotion Details
    name = Column(
        String(255), 
        nullable=False,
        index=True,  # Added index
        comment="Display name of the promotion"
    )
    description = Column(
        String(1000), 
        nullable=True,
        comment="Detailed description of the offer"
    )
    promotion_type = Column(
        Enum(PromotionType, schema='data_playground'), 
        nullable=False,
        index=True,
        comment="Type of discount offered"
    )
    status = Column(
        Enum(PromotionStatus, schema='data_playground'), 
        nullable=False, 
        default=PromotionStatus.DRAFT,
        index=True,
        comment="Current status of the promotion"
    )
    
    # Discount Configuration
    discount_value = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Amount of discount (percentage or fixed amount)"
    )
    minimum_purchase_amount = Column(
        Float, 
        nullable=True,
        index=True,  # Added index
        comment="Minimum order value required"
    )
    maximum_discount_amount = Column(
        Float, 
        nullable=True,
        index=True,  # Added index
        comment="Maximum discount allowed"
    )
    
    # Usage Limits
    usage_limit_per_user = Column(
        Integer, 
        nullable=True,
        index=True,  # Added index
        comment="Maximum times a user can use this promotion"
    )
    usage_limit_total = Column(
        Integer, 
        nullable=True,
        index=True,  # Added index
        comment="Maximum total uses allowed"
    )
    current_usage_count = Column(
        Integer, 
        nullable=False, 
        default=0,
        index=True,  # Added index
        comment="Number of times promotion has been used"
    )
    
    # Validity Period
    valid_from = Column(
        DateTime(timezone=True), 
        nullable=False,
        index=True,  # Added index
        comment="When the promotion becomes active"
    )
    valid_until = Column(
        DateTime(timezone=True), 
        nullable=False,
        index=True,  # Added index
        comment="When the promotion expires"
    )
    
    # Applicability
    applicability = Column(
        Enum(PromotionApplicability, schema='data_playground'), 
        nullable=False,
        index=True,
        comment="What items the promotion applies to"
    )
    applicable_product_ids = Column(
        ARRAY(UUID), 
        nullable=True,
        comment="List of product IDs eligible for promotion"
    )
    applicable_categories = Column(
        ARRAY(String), 
        nullable=True,
        comment="List of product categories eligible for promotion"
    )
    
    # Promotion Codes
    promo_code = Column(
        String(50), 
        nullable=True,
        index=True,  # Changed from unique=True to just index=True
        comment="Code users enter to apply promotion"
    )
    requires_code = Column(
        Boolean, 
        nullable=False, 
        default=False,
        index=True,  # Added index
        comment="Whether a code is required to use promotion"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the promotion was created"
    )
    updated_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the promotion was last updated"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    terms_conditions = Column(
        String(2000), 
        nullable=True,
        comment="Terms and conditions for the promotion"
    )
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional promotion data stored as JSON"
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
        # Unique constraint for promo code must include partition key
        UniqueConstraint('promo_code', 'partition_key', name='uq_shop_promotions_code'),
        
        # Composite index for active promotions by shop
        Index('ix_shop_promotions_shop_status', 'shop_id', 'status'),
        
        # Composite index for valid promotions by time
        Index('ix_shop_promotions_validity', 'valid_from', 'valid_until', 'status'),
        
        # Composite index for promotions by type and status
        Index('ix_shop_promotions_type_status', 'promotion_type', 'status'),
        
        # Composite index for promotions by applicability
        Index('ix_shop_promotions_applicability', 'applicability', 'status'),
        
        # Composite index for usage tracking
        Index('ix_shop_promotions_usage', 'current_usage_count', 'usage_limit_total'),
        
        # Foreign key constraint with partition key
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['data_playground.shops.id', 'data_playground.shops.partition_key'],
            name='fk_shop_promotion_shop',
            comment="Foreign key relationship to the shops table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores promotion data with hourly partitioning for efficient querying'
        }
    )

    # Helper Methods for Validation
    def is_valid(self, current_time=None):
        """Check if promotion is currently valid"""
        if not current_time:
            current_time = datetime.utcnow()
        
        return (
            self.status == PromotionStatus.ACTIVE and
            self.valid_from <= current_time <= self.valid_until and
            (not self.usage_limit_total or self.current_usage_count < self.usage_limit_total)
        )

    async def can_be_used_by_user(self, db, user_id):
        """Check if user can use this promotion"""
        if not self.usage_limit_per_user:
            return True
        
        user_usage_count = await self.usages.filter_by(user_id=user_id).count()
        return user_usage_count < self.usage_limit_per_user

    def is_applicable_to_product(self, product_id, product_category=None):
        """Check if promotion applies to a specific product"""
        if self.applicability == PromotionApplicability.ALL_PRODUCTS:
            return True
        
        if self.applicability == PromotionApplicability.SPECIFIC_PRODUCTS:
            return product_id in (self.applicable_product_ids or [])
        
        if self.applicability == PromotionApplicability.SPECIFIC_CATEGORIES:
            return product_category in (self.applicable_categories or [])
        
        return True

    # Helper Methods for Usage
    async def record_usage(self, db, user_id, order_id, discount_amount, **usage_data):
        """Record a usage of the promotion"""
        if not self.is_valid():
            raise ValueError("Promotion is not valid")
        
        if not await self.can_be_used_by_user(db, user_id):
            raise ValueError("User has exceeded usage limit")
        
        usage = await ShopPromotionUsage.create_with_partition(
            db,
            promotion_id=self.id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount_amount,
            **usage_data
        )
        
        self.current_usage_count += 1
        await db.commit()
        
        return usage

    # Helper Methods for Analysis
    async def get_usage_stats(self, db, start_time=None, end_time=None):
        """Get usage statistics for the promotion"""
        query = self.usages
        if start_time:
            query = query.filter(ShopPromotionUsage.event_time >= start_time)
        if end_time:
            query = query.filter(ShopPromotionUsage.event_time <= end_time)
        
        usages = await query.all()
        return {
            'total_uses': len(usages),
            'total_discount_amount': sum(usage.discount_amount for usage in usages),
            'average_discount': sum(usage.discount_amount for usage in usages) / len(usages) if usages else 0,
            'unique_users': len(set(usage.user_id for usage in usages))
        }

class ShopPromotionUsage(Base, PartitionedModel):
    """
    Records each use of a promotion, tracking who used it, when,
    and how much discount was applied.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - promotion_id is indexed for promotion-based queries
    - user_id is indexed for user-based queries
    - order_id is indexed for order-based queries
    - created_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    """
    __tablename__ = 'shop_promotion_usages'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the usage record"
    )
    promotion_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the promotion used"
    )
    user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the user who used the promotion"
    )
    order_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,
        comment="ID of the order where promotion was applied"
    )
    
    # Usage Details
    discount_amount = Column(
        Float, 
        nullable=False,
        index=True,  # Added index
        comment="Amount of discount applied"
    )
    promo_code_used = Column(
        String(50), 
        nullable=True,
        index=True,  # Added index
        comment="Promotion code entered (if applicable)"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the promotion was used"
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
        comment="Additional usage data stored as JSON"
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
        # Composite index for promotion usage by user
        Index('ix_shop_promotion_usages_user', 'promotion_id', 'user_id'),
        
        # Composite index for promotion usage by order
        Index('ix_shop_promotion_usages_order', 'promotion_id', 'order_id'),
        
        # Composite index for promotion usage over time
        Index('ix_shop_promotion_usages_time', 'promotion_id', 'created_time'),
        
        # Foreign key constraints with partition key
        ForeignKeyConstraint(
            ['promotion_id', 'partition_key'],
            ['data_playground.shop_promotions.id', 'data_playground.shop_promotions.partition_key'],
            name='fk_shop_promotion_usage_promotion',
            comment="Foreign key relationship to the shop_promotions table"
        ),
        ForeignKeyConstraint(
            ['user_id', 'partition_key'],
            ['data_playground.users.id', 'data_playground.users.partition_key'],
            name='fk_shop_promotion_usage_user',
            comment="Foreign key relationship to the users table"
        ),
        ForeignKeyConstraint(
            ['order_id', 'partition_key'],
            ['data_playground.shop_orders.id', 'data_playground.shop_orders.partition_key'],
            name='fk_shop_promotion_usage_order',
            comment="Foreign key relationship to the shop_orders table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores promotion usage data with hourly partitioning for efficient querying'
        }
    )
