from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, Integer, UUID, Index
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
import enum

class ReviewType(enum.Enum):
    """Types of reviews that can be created"""
    SHOP = "shop"  # Review for the overall shop
    PRODUCT = "product"  # Review for a specific product

class ReviewStatus(enum.Enum):
    """Possible states for a review"""
    PENDING = "pending"  # Awaiting moderation
    APPROVED = "approved"  # Visible to public
    REJECTED = "rejected"  # Not approved for display
    REPORTED = "reported"  # Flagged for review
    REMOVED = "removed"  # Taken down after being live

class FakeUserShopReview(Base, PartitionedModel):
    """
    Represents a review written by a user for a shop or product.
    Reviews can receive votes and affect shop/product metrics.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - review_type is indexed for filtering review types
    - status is indexed for filtering by moderation status
    - rating is indexed for rating-based queries
    - fake_user_id is indexed for user-based queries
    - fake_user_shop_id is indexed for shop-based queries
    - product_id is indexed for product-based queries
    - created_time is indexed for time-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'fake_user_shop_reviews'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the review"
    )
    fake_user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the user who wrote the review"
    )
    fake_user_shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the shop being reviewed"
    )
    product_id = Column(
        UUID(as_uuid=True), 
        nullable=True,
        index=True,  # Added index
        comment="ID of the product being reviewed (if applicable)"
    )
    order_id = Column(
        UUID(as_uuid=True), 
        nullable=True,
        index=True,  # Added index
        comment="ID of the order associated with this review (if applicable)"
    )
    
    # Review Details
    review_type = Column(
        Enum(ReviewType), 
        nullable=False,
        index=True,  # Added index
        comment="Whether this is a shop or product review"
    )
    status = Column(
        Enum(ReviewStatus), 
        nullable=False, 
        default=ReviewStatus.PENDING,
        index=True,  # Added index
        comment="Current moderation status of the review"
    )
    rating = Column(
        Integer, 
        nullable=False,
        index=True,  # Added index
        comment="Rating score (typically 1-5)"
    )
    title = Column(
        String(255), 
        nullable=True,
        comment="Review title or summary"
    )
    content = Column(
        String(2000), 
        nullable=False,
        comment="Main review text"
    )
    
    # Review Metrics
    helpful_votes = Column(
        Integer, 
        nullable=False, 
        default=0,
        index=True,  # Added index
        comment="Number of users who found this review helpful"
    )
    not_helpful_votes = Column(
        Integer, 
        nullable=False, 
        default=0,
        index=True,  # Added index
        comment="Number of users who found this review not helpful"
    )
    is_verified_purchase = Column(
        Boolean, 
        nullable=False, 
        default=False,
        index=True,  # Added index
        comment="Whether the reviewer purchased the item/used the shop"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the review was written"
    )
    updated_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        index=True,  # Added index
        comment="When the review was last edited"
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
        comment="Additional review data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False, 
        index=True,
        comment="Key used for time-based table partitioning"
    )

    # Relationships
    # Votes cast on this review
    votes = relationship(
        "FakeUserShopReviewVote",
        backref=backref("review", lazy="joined"),
        foreign_keys="FakeUserShopReviewVote.review_id",
        lazy="dynamic"
    )

    # Indexes for common queries
    __table_args__ = (
        # Composite index for shop reviews by rating
        Index('ix_fake_user_shop_reviews_shop_rating', 'fake_user_shop_id', 'rating', 'status'),
        
        # Composite index for product reviews by rating
        Index('ix_fake_user_shop_reviews_product_rating', 'product_id', 'rating', 'status'),
        
        # Composite index for user reviews by type
        Index('ix_fake_user_shop_reviews_user_type', 'fake_user_id', 'review_type', 'status'),
        
        # Composite index for verified purchase reviews
        Index('ix_fake_user_shop_reviews_verified', 'is_verified_purchase', 'rating', 'status'),
        
        # Composite index for helpful votes ranking
        Index('ix_fake_user_shop_reviews_helpful', 'helpful_votes', 'status'),
        
        # Foreign key constraints
        ForeignKeyConstraint(
            ['fake_user_id'], ['data_playground.fake_users.id'],
            name='fk_fake_user_shop_review_user',
            comment="Foreign key relationship to the fake_users table"
        ),
        ForeignKeyConstraint(
            ['fake_user_shop_id'], ['data_playground.fake_user_shops.id'],
            name='fk_fake_user_shop_review_shop',
            comment="Foreign key relationship to the fake_user_shops table"
        ),
        ForeignKeyConstraint(
            ['product_id'], ['data_playground.fake_user_shop_products.id'],
            name='fk_fake_user_shop_review_product',
            comment="Foreign key relationship to the fake_user_shop_products table"
        ),
        ForeignKeyConstraint(
            ['order_id'], ['data_playground.fake_user_shop_orders.id'],
            name='fk_fake_user_shop_review_order',
            comment="Foreign key relationship to the fake_user_shop_orders table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores review data with hourly partitioning for efficient querying'
        }
    )

    # Helper Methods for Vote Operations
    async def add_vote(self, db, user_id, is_helpful):
        """Add a vote to the review"""
        vote = await FakeUserShopReviewVote.create_with_partition(
            db,
            review_id=self.id,
            fake_user_id=user_id,
            is_helpful=is_helpful
        )
        
        # Update vote counts
        if is_helpful:
            self.helpful_votes += 1
        else:
            self.not_helpful_votes += 1
        
        await db.commit()
        return vote

    async def get_votes(self, db, helpful_only=None):
        """Get votes for this review"""
        query = self.votes
        if helpful_only is not None:
            query = query.filter_by(is_helpful=helpful_only)
        return await query.all()

    # Helper Methods for Status Updates
    async def update_status(self, db, new_status, **update_data):
        """Update review status"""
        self.status = new_status
        self.updated_time = datetime.utcnow()
        
        # Update any additional fields
        for key, value in update_data.items():
            setattr(self, key, value)
        
        await db.commit()
        return self

    # Helper Methods for Metrics
    async def calculate_helpfulness_score(self):
        """Calculate helpfulness score"""
        total_votes = self.helpful_votes + self.not_helpful_votes
        if total_votes == 0:
            return 0
        return (self.helpful_votes / total_votes) * 100

class FakeUserShopReviewVote(Base, PartitionedModel):
    """
    Represents a vote cast by a user on a review, indicating whether
    they found it helpful or not.
    
    Indexing Strategy:
    - Primary key (id) is automatically indexed
    - review_id is indexed for review-based queries
    - fake_user_id is indexed for user-based queries
    - is_helpful is indexed for helpful/not helpful filtering
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    """
    __tablename__ = 'fake_user_shop_review_votes'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the vote"
    )
    review_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the review being voted on"
    )
    fake_user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        index=True,  # Added index
        comment="ID of the user casting the vote"
    )
    
    # Vote Details
    is_helpful = Column(
        Boolean, 
        nullable=False,
        index=True,  # Added index
        comment="Whether the user found the review helpful"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        index=True,  # Added index
        comment="When the vote was cast"
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
        comment="Additional vote data stored as JSON"
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
        # Composite index for user votes on reviews
        Index('ix_fake_user_shop_review_votes_user_review', 'fake_user_id', 'review_id'),
        
        # Composite index for helpful votes by review
        Index('ix_fake_user_shop_review_votes_helpful', 'review_id', 'is_helpful'),
        
        # Foreign key constraints
        ForeignKeyConstraint(
            ['review_id'], ['data_playground.fake_user_shop_reviews.id'],
            name='fk_fake_user_shop_review_vote_review',
            comment="Foreign key relationship to the fake_user_shop_reviews table"
        ),
        ForeignKeyConstraint(
            ['fake_user_id'], ['data_playground.fake_users.id'],
            name='fk_fake_user_shop_review_vote_user',
            comment="Foreign key relationship to the fake_users table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores review vote data with hourly partitioning for efficient querying'
        }
    )
