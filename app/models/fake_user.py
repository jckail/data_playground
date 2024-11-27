from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, Boolean, JSON, UUID, Index, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
from .user_metrics import FakeUserMetricsDaily, FakeUserMetricsHourly

class FakeUser(Base, PartitionedModel):
    """
    Represents a fake user in the system for testing and development purposes.
    Includes comprehensive user data and relationships to all user-related entities.
    
    Indexing Strategy:
    - Composite primary key (id, partition_key) for partitioning support
    - username is indexed for unique constraint and frequent lookups
    - email is indexed for frequent lookups and authentication
    - status is indexed for filtering active/inactive users
    - created_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'fake_users'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the user"
    )
    username = Column(
        String(50), 
        nullable=False,
        index=True,
        comment="User's unique username for login and display"
    )
    email = Column(
        String(255), 
        nullable=False,
        index=True,
        comment="User's email address for notifications and communication"
    )
    phone_number = Column(
        String(20), 
        nullable=True,
        comment="User's contact phone number (optional)"
    )
    status = Column(
        Boolean, 
        nullable=False, 
        default=True,
        index=True,
        comment="User account status (true=active, false=inactive)"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,
        comment="When the user account was created"
    )
    deactivated_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        index=True,
        comment="When the user account was deactivated (if applicable)"
    )
    last_login_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        index=True,
        comment="Last time the user logged in"
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
        comment="Additional user data stored as JSON"
    )

    # Relationships
    # Shops owned by this user
    owned_shops = relationship(
        "FakeUserShop",
        backref=backref("owner", lazy="joined"),
        foreign_keys="FakeUserShop.fake_user_owner_id",
        lazy="dynamic"
    )
    
    # Orders placed by this user
    orders_placed = relationship(
        "FakeUserShopOrder",
        backref=backref("customer", lazy="joined"),
        foreign_keys="FakeUserShopOrder.fake_user_id",
        lazy="dynamic"
    )
    
    # Payment methods saved by this user
    payment_methods = relationship(
        "FakeUserPaymentMethod",
        backref=backref("user", lazy="joined"),
        foreign_keys="FakeUserPaymentMethod.fake_user_id",
        lazy="dynamic"
    )
    
    # Reviews written by this user
    reviews_written = relationship(
        "FakeUserShopReview",
        backref=backref("reviewer", lazy="joined"),
        foreign_keys="FakeUserShopReview.fake_user_id",
        lazy="dynamic"
    )
    
    # Invoices associated with this user
    invoices = relationship(
        "FakeUserInvoice",
        backref=backref("user", lazy="joined"),
        foreign_keys="FakeUserInvoice.fake_user_id",
        lazy="dynamic"
    )
    
    # Promotions used by this user
    promotion_usages = relationship(
        "FakeUserShopPromotionUsage",
        backref=backref("user", lazy="joined"),
        foreign_keys="FakeUserShopPromotionUsage.fake_user_id",
        lazy="dynamic"
    )
    
    # Votes cast by this user on reviews
    review_votes = relationship(
        "FakeUserShopReviewVote",
        backref=backref("voter", lazy="joined"),
        foreign_keys="FakeUserShopReviewVote.fake_user_id",
        lazy="dynamic"
    )
    
    # Hourly metrics for this user
    hourly_metrics = relationship(
        "FakeUserMetricsHourly",
        backref=backref("user", lazy="joined"),
        foreign_keys="FakeUserMetricsHourly.fake_user_id",
        lazy="dynamic"
    )
    
    # Daily metrics for this user
    daily_metrics = relationship(
        "FakeUserMetricsDaily",
        backref=backref("user", lazy="joined"),
        foreign_keys="FakeUserMetricsDaily.fake_user_id",
        lazy="dynamic"
    )
    
    # Events associated with this user
    events = relationship(
        "GlobalEvent",
        backref=backref("user", lazy="joined"),
        foreign_keys="GlobalEvent.fake_user_id",
        lazy="dynamic"
    )

    # Indexes and Constraints
    __table_args__ = (
        # Unique constraints must include partition_key
        UniqueConstraint('username', 'partition_key', name='uq_fake_users_username'),
        UniqueConstraint('id', 'partition_key', name='uq_fake_users_id'),
        
        # Composite index for status and created_time for filtering active users by creation date
        Index('ix_fake_users_status_created_time', 'status', 'created_time'),
        
        # Composite index for status and last_login_time for filtering active users by last login
        Index('ix_fake_users_status_last_login', 'status', 'last_login_time'),
        
        # Composite index for event_time and status for time-based queries with status filter
        Index('ix_fake_users_event_time_status', 'event_time', 'status'),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores fake user data with hourly partitioning for efficient querying'
        }
    )

    # Helper Methods for Shop Operations
    async def create_shop(self, db, **shop_data):
        """Create a new shop owned by this user"""
        from .shop import FakeUserShop
        shop = await FakeUserShop.create_with_partition(db, fake_user_owner_id=self.id, **shop_data)
        return shop

    async def get_owned_shops(self, db, active_only=True):
        """Get shops owned by this user"""
        query = self.owned_shops
        if active_only:
            query = query.filter_by(status=True)
        return await query.all()

    # Helper Methods for Order Operations
    async def place_order(self, db, shop_id, **order_data):
        """Place a new order at a shop"""
        from .shop_order import FakeUserShopOrder
        order = await FakeUserShopOrder.create_with_partition(
            db, fake_user_id=self.id, fake_user_shop_id=shop_id, **order_data
        )
        return order

    async def get_orders(self, db, status=None):
        """Get orders placed by this user"""
        query = self.orders_placed
        if status:
            query = query.filter_by(status=status)
        return await query.all()

    # Helper Methods for Payment Operations
    async def add_payment_method(self, db, **payment_method_data):
        """Add a new payment method"""
        from .payment_method import FakeUserPaymentMethod
        payment_method = await FakeUserPaymentMethod.create_with_partition(
            db, fake_user_id=self.id, **payment_method_data
        )
        return payment_method

    async def get_payment_methods(self, db, active_only=True):
        """Get user's payment methods"""
        query = self.payment_methods
        if active_only:
            query = query.filter_by(status='ACTIVE')
        return await query.all()

    # Helper Methods for Review Operations
    async def write_review(self, db, shop_id, **review_data):
        """Write a review for a shop or product"""
        from .shop_review import FakeUserShopReview
        review = await FakeUserShopReview.create_with_partition(
            db, fake_user_id=self.id, fake_user_shop_id=shop_id, **review_data
        )
        return review

    async def get_reviews(self, db):
        """Get reviews written by this user"""
        return await self.reviews_written.all()

    # Helper Methods for Promotion Operations
    async def use_promotion(self, db, promotion_id, order_id, **usage_data):
        """Use a promotion on an order"""
        from .shop_promotion import FakeUserShopPromotionUsage
        usage = await FakeUserShopPromotionUsage.create_with_partition(
            db, fake_user_id=self.id, promotion_id=promotion_id, 
            order_id=order_id, **usage_data
        )
        return usage

    # Helper Methods for Metrics
    async def get_metrics(self, db, timeframe='daily', start_time=None, end_time=None):
        """Get user metrics for a specific timeframe"""
        MetricsModel = FakeUserMetricsDaily if timeframe == 'daily' else FakeUserMetricsHourly
        query = self.daily_metrics if timeframe == 'daily' else self.hourly_metrics
        if start_time:
            query = query.filter(MetricsModel.event_time >= start_time)
        if end_time:
            query = query.filter(MetricsModel.event_time <= end_time)
        return await query.all()
