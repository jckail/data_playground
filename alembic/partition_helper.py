import logging
from datetime import datetime, timedelta
from app.database import execute_ddl

logger = logging.getLogger(__name__)

def create_partitions_for_table(table_name: str, start_date: datetime, end_date: datetime):
    """Create partitions for a specific table within a date range"""
    current_date = start_date
    while current_date <= end_date:
        partition_name = current_date.strftime("%Y_%m")
        next_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1)
        next_partition = next_month.strftime("%Y_%m")
        
        try:
            execute_ddl(f"""
                CREATE TABLE IF NOT EXISTS data_playground.{table_name}_{partition_name}
                PARTITION OF data_playground.{table_name}
                FOR VALUES FROM ('{partition_name}') TO ('{next_partition}')
            """)
            logger.info(f"Created partition {table_name}_{partition_name}")
        except Exception as e:
            logger.error(f"Error creating partition {table_name}_{partition_name}: {str(e)}")
            raise
            
        # Move to next month
        current_date = next_month

def create_initial_partitions():
    """Create initial partitions for all partitioned tables."""
    try:
        # Calculate date range (365 days in past to 365 days in future)
        now = datetime.utcnow()
        start_date = (now - timedelta(days=365)).replace(day=1)
        end_date = (now + timedelta(days=365)).replace(day=1)
        
        logger.info(f"Creating partitions from {start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}")
        
        # List of partitioned tables
        tables = [
            'global_entities', 'global_events', 'users', 'shops', 'shop_products',
            'shop_orders', 'shop_order_items', 'shop_order_payments',
            'shop_reviews', 'shop_review_votes', 'shop_inventory_logs',
            'shop_promotions', 'shop_promotion_usages', 'invoices',
            'invoice_payments', 'user_payment_methods',
            'user_metrics_hourly', 'user_metrics_daily',
            'shop_metrics_hourly', 'shop_metrics_daily',
            'shop_product_metrics_hourly', 'shop_product_metrics_daily'
        ]
        
        # Create partitions for each table
        for table in tables:
            logger.info(f"Creating partitions for table: {table}")
            create_partitions_for_table(table, start_date, end_date)
            
        return True
    except Exception as e:
        logger.error(f"Error creating partitions: {str(e)}")
        raise

def create_partition_for_month(table_name: str, date: datetime):
    """Create a partition for a specific month if it doesn't exist"""
    try:
        partition_name = date.strftime("%Y_%m")
        next_month = (date.replace(day=1) + timedelta(days=32)).replace(day=1)
        next_partition = next_month.strftime("%Y_%m")
        
        execute_ddl(f"""
            CREATE TABLE IF NOT EXISTS data_playground.{table_name}_{partition_name}
            PARTITION OF data_playground.{table_name}
            FOR VALUES FROM ('{partition_name}') TO ('{next_partition}')
        """)
        logger.info(f"Created partition {table_name}_{partition_name}")
        return True
    except Exception as e:
        logger.error(f"Error creating partition {table_name}_{partition_name}: {str(e)}")
        raise
