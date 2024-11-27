from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, Float, Integer, ForeignKeyConstraint, UUID, JSON
from datetime import datetime

class FakeUserMetricsHourly(Base, PartitionedModel):
    __tablename__ = 'fake_user_metrics_hourly'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True)
    fake_user_id = Column(UUID(as_uuid=True), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    
    # Order Metrics
    orders_placed_count = Column(Integer, nullable=False, default=0)
    orders_cancelled_count = Column(Integer, nullable=False, default=0)
    total_order_amount = Column(Float, nullable=False, default=0.0)
    avg_order_amount = Column(Float, nullable=False, default=0.0)
    unique_shops_ordered_from = Column(Integer, nullable=False, default=0)
    
    # Payment Metrics
    total_amount_paid = Column(Float, nullable=False, default=0.0)
    total_amount_refunded = Column(Float, nullable=False, default=0.0)
    successful_payments_count = Column(Integer, nullable=False, default=0)
    failed_payments_count = Column(Integer, nullable=False, default=0)
    
    # Review Metrics
    reviews_written_count = Column(Integer, nullable=False, default=0)
    avg_rating_given = Column(Float, nullable=True)
    helpful_votes_received = Column(Integer, nullable=False, default=0)
    
    # Promotion Metrics
    promotions_used_count = Column(Integer, nullable=False, default=0)
    total_discount_amount = Column(Float, nullable=False, default=0.0)
    
    # Additional Metrics
    cart_abandonment_count = Column(Integer, nullable=False, default=0)
    total_items_purchased = Column(Integer, nullable=False, default=0)
    extra_metrics = Column(JSON, nullable=True, default={})

    __table_args__ = (
        ForeignKeyConstraint(
            ['fake_user_id'], ['data_playground.fake_users.id'],
            name='fk_fake_user_metrics_hourly_user'
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )

class FakeUserMetricsDaily(Base, PartitionedModel):
    __tablename__ = 'fake_user_metrics_daily'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True)
    fake_user_id = Column(UUID(as_uuid=True), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    
    # Order Metrics
    orders_placed_count = Column(Integer, nullable=False, default=0)
    orders_cancelled_count = Column(Integer, nullable=False, default=0)
    total_order_amount = Column(Float, nullable=False, default=0.0)
    avg_order_amount = Column(Float, nullable=False, default=0.0)
    unique_shops_ordered_from = Column(Integer, nullable=False, default=0)
    
    # Payment Metrics
    total_amount_paid = Column(Float, nullable=False, default=0.0)
    total_amount_refunded = Column(Float, nullable=False, default=0.0)
    successful_payments_count = Column(Integer, nullable=False, default=0)
    failed_payments_count = Column(Integer, nullable=False, default=0)
    
    # Review Metrics
    reviews_written_count = Column(Integer, nullable=False, default=0)
    avg_rating_given = Column(Float, nullable=True)
    helpful_votes_received = Column(Integer, nullable=False, default=0)
    
    # Promotion Metrics
    promotions_used_count = Column(Integer, nullable=False, default=0)
    total_discount_amount = Column(Float, nullable=False, default=0.0)
    
    # Additional Metrics
    cart_abandonment_count = Column(Integer, nullable=False, default=0)
    total_items_purchased = Column(Integer, nullable=False, default=0)
    extra_metrics = Column(JSON, nullable=True, default={})

    __table_args__ = (
        ForeignKeyConstraint(
            ['fake_user_id'], ['data_playground.fake_users.id'],
            name='fk_fake_user_metrics_daily_user'
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )
