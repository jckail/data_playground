from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, Float, Integer, ForeignKeyConstraint, UUID, JSON, String
from datetime import datetime

class ShopProductMetricsHourly(Base, PartitionedModel):
    __tablename__ = 'shop_product_metrics_hourly'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    
    # Sales Metrics
    units_sold = Column(Integer, nullable=False, default=0)
    units_refunded = Column(Integer, nullable=False, default=0)
    gross_sales = Column(Float, nullable=False, default=0.0)
    net_sales = Column(Float, nullable=False, default=0.0)
    
    # Inventory Metrics
    current_stock_level = Column(Integer, nullable=False, default=0)
    stock_replenishment_count = Column(Integer, nullable=False, default=0)
    time_out_of_stock_minutes = Column(Integer, nullable=False, default=0)
    
    # Price Metrics
    avg_selling_price = Column(Float, nullable=False, default=0.0)
    min_selling_price = Column(Float, nullable=False, default=0.0)
    max_selling_price = Column(Float, nullable=False, default=0.0)
    
    # Review Metrics
    reviews_count = Column(Integer, nullable=False, default=0)
    avg_rating = Column(Float, nullable=True)
    one_star_reviews_count = Column(Integer, nullable=False, default=0)
    five_star_reviews_count = Column(Integer, nullable=False, default=0)
    
    # Promotion Metrics
    times_discounted = Column(Integer, nullable=False, default=0)
    total_discount_amount = Column(Float, nullable=False, default=0.0)
    
    # Additional Metrics
    cart_additions_count = Column(Integer, nullable=False, default=0)
    cart_removals_count = Column(Integer, nullable=False, default=0)
    page_views = Column(Integer, nullable=False, default=0)
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
            ['product_id', 'partition_key'],
            ['data_playground.shop_products.id', 'data_playground.shop_products.partition_key'],
            name='fk_shop_product_metrics_hourly_product'
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )

class ShopProductMetricsDaily(Base, PartitionedModel):
    __tablename__ = 'shop_product_metrics_daily'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    id = Column(UUID(as_uuid=True), primary_key=True)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    
    # Sales Metrics
    units_sold = Column(Integer, nullable=False, default=0)
    units_refunded = Column(Integer, nullable=False, default=0)
    gross_sales = Column(Float, nullable=False, default=0.0)
    net_sales = Column(Float, nullable=False, default=0.0)
    
    # Inventory Metrics
    current_stock_level = Column(Integer, nullable=False, default=0)
    stock_replenishment_count = Column(Integer, nullable=False, default=0)
    time_out_of_stock_minutes = Column(Integer, nullable=False, default=0)
    
    # Price Metrics
    avg_selling_price = Column(Float, nullable=False, default=0.0)
    min_selling_price = Column(Float, nullable=False, default=0.0)
    max_selling_price = Column(Float, nullable=False, default=0.0)
    
    # Review Metrics
    reviews_count = Column(Integer, nullable=False, default=0)
    avg_rating = Column(Float, nullable=True)
    one_star_reviews_count = Column(Integer, nullable=False, default=0)
    five_star_reviews_count = Column(Integer, nullable=False, default=0)
    
    # Promotion Metrics
    times_discounted = Column(Integer, nullable=False, default=0)
    total_discount_amount = Column(Float, nullable=False, default=0.0)
    
    # Additional Metrics
    cart_additions_count = Column(Integer, nullable=False, default=0)
    cart_removals_count = Column(Integer, nullable=False, default=0)
    page_views = Column(Integer, nullable=False, default=0)
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
            ['product_id', 'partition_key'],
            ['data_playground.shop_products.id', 'data_playground.shop_products.partition_key'],
            name='fk_shop_product_metrics_daily_product'
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )
