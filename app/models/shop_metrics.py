from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, Float, Integer, ForeignKeyConstraint, UUID, JSON, String
from datetime import datetime

class FakeUserShopMetricsHourly(Base, PartitionedModel):
    __tablename__ = 'fake_user_shop_metrics_hourly'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True)
    fake_user_shop_id = Column(UUID(as_uuid=True), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    
    # Order Metrics
    orders_received_count = Column(Integer, nullable=False, default=0)
    orders_cancelled_count = Column(Integer, nullable=False, default=0)
    total_order_amount = Column(Float, nullable=False, default=0.0)
    avg_order_amount = Column(Float, nullable=False, default=0.0)
    unique_customers_count = Column(Integer, nullable=False, default=0)
    
    # Product Metrics
    total_products_sold = Column(Integer, nullable=False, default=0)
    unique_products_sold = Column(Integer, nullable=False, default=0)
    low_stock_products_count = Column(Integer, nullable=False, default=0)
    out_of_stock_products_count = Column(Integer, nullable=False, default=0)
    
    # Revenue Metrics
    gross_revenue = Column(Float, nullable=False, default=0.0)
    net_revenue = Column(Float, nullable=False, default=0.0)
    total_discounts_given = Column(Float, nullable=False, default=0.0)
    total_refunds_amount = Column(Float, nullable=False, default=0.0)
    
    # Review Metrics
    reviews_received_count = Column(Integer, nullable=False, default=0)
    avg_rating_received = Column(Float, nullable=True)
    one_star_reviews_count = Column(Integer, nullable=False, default=0)
    five_star_reviews_count = Column(Integer, nullable=False, default=0)
    
    # Promotion Metrics
    active_promotions_count = Column(Integer, nullable=False, default=0)
    promotions_used_count = Column(Integer, nullable=False, default=0)
    
    # Additional Metrics
    inventory_value = Column(Float, nullable=False, default=0.0)
    extra_metrics = Column(JSON, nullable=True, default={})

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['fake_user_shop_id', 'partition_key'],
            ['data_playground.fake_user_shops.id', 'data_playground.fake_user_shops.partition_key'],
            name='fk_fake_user_shop_metrics_hourly_shop'
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )

class FakeUserShopMetricsDaily(Base, PartitionedModel):
    __tablename__ = 'fake_user_shop_metrics_daily'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True)
    fake_user_shop_id = Column(UUID(as_uuid=True), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    
    # Order Metrics
    orders_received_count = Column(Integer, nullable=False, default=0)
    orders_cancelled_count = Column(Integer, nullable=False, default=0)
    total_order_amount = Column(Float, nullable=False, default=0.0)
    avg_order_amount = Column(Float, nullable=False, default=0.0)
    unique_customers_count = Column(Integer, nullable=False, default=0)
    
    # Product Metrics
    total_products_sold = Column(Integer, nullable=False, default=0)
    unique_products_sold = Column(Integer, nullable=False, default=0)
    low_stock_products_count = Column(Integer, nullable=False, default=0)
    out_of_stock_products_count = Column(Integer, nullable=False, default=0)
    
    # Revenue Metrics
    gross_revenue = Column(Float, nullable=False, default=0.0)
    net_revenue = Column(Float, nullable=False, default=0.0)
    total_discounts_given = Column(Float, nullable=False, default=0.0)
    total_refunds_amount = Column(Float, nullable=False, default=0.0)
    
    # Review Metrics
    reviews_received_count = Column(Integer, nullable=False, default=0)
    avg_rating_received = Column(Float, nullable=True)
    one_star_reviews_count = Column(Integer, nullable=False, default=0)
    five_star_reviews_count = Column(Integer, nullable=False, default=0)
    
    # Promotion Metrics
    active_promotions_count = Column(Integer, nullable=False, default=0)
    promotions_used_count = Column(Integer, nullable=False, default=0)
    
    # Additional Metrics
    inventory_value = Column(Float, nullable=False, default=0.0)
    extra_metrics = Column(JSON, nullable=True, default={})

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['fake_user_shop_id', 'partition_key'],
            ['data_playground.fake_user_shops.id', 'data_playground.fake_user_shops.partition_key'],
            name='fk_fake_user_shop_metrics_daily_shop'
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )
