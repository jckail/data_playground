import logging
import sqlalchemy as sa
from datetime import datetime, timedelta
from app.models import *
from sqlalchemy import inspect, text
from typing import Union, List
from sqlalchemy.ext.asyncio import AsyncConnection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_table_model(table_name: str):
    """Look up SQLAlchemy model class for a given table name"""
    logger.info(f"Looking up model for table: {table_name}")
    for model in Base.__subclasses__():
        if hasattr(model, '__tablename__') and model.__tablename__ == table_name:
            logger.info(f"Found model: {model.__name__}")
            return model
    logger.warning(f"No model found for table: {table_name}")
    return None

def get_partition_info(model):
    """Extract partition configuration from model class"""
    logger.info(f"Getting partition info for model: {model.__name__}")
    if not hasattr(model, '__partitiontype__') or not hasattr(model, '__partition_field__'):
        logger.warning(f"No partition configuration found for model: {model.__name__}")
        return None
    
    info = {
        'type': model.__partitiontype__,
        'field': model.__partition_field__
    }
    logger.info(f"Partition info for {model.__name__}: {info}")
    return info

def generate_partition_name(tablename: str, partition_key: str) -> str:
    """Generate standardized partition table name"""
    return f"{tablename}_p_{partition_key.replace('-', '_').replace(':', '_')}".lower()

async def check_and_create_partition(connection: AsyncConnection, table_name: str, start_range: datetime, end_range: datetime = None):
    """Create partition(s) for a table within the specified time range"""
    try:
        logger.info(f"Creating partitions for table {table_name} from {start_range} to {end_range or start_range}")
        
        # Look up model for the table
        model = get_table_model(table_name)
        if not model:
            logger.error(f"No model found for table {table_name}")
            return False

        # Get partition configuration
        partition_info = get_partition_info(model)
        if not partition_info:
            logger.error(f"No partition configuration found for model {model.__name__}")
            return False

        # If no end range specified, use start range
        if end_range is None:
            end_range = start_range

        current_time = start_range
        partition_type = partition_info['type']
        logger.info(f"Creating {partition_type} partitions for {table_name}")

        while current_time <= end_range:
            try:
                if partition_type == "hourly":
                    partition_key = current_time.strftime("%Y-%m-%dT%H:00:00")
                    next_time = current_time + timedelta(hours=1)
                    next_key = next_time.strftime("%Y-%m-%dT%H:00:00")
                elif partition_type == "daily":
                    partition_key = current_time.strftime("%Y-%m-%d")
                    next_time = current_time + timedelta(days=1)
                    next_key = next_time.strftime("%Y-%m-%d")
                else:
                    logger.error(f"Unsupported partition type {partition_type} for table {table_name}")
                    return False

                partition_name = generate_partition_name(table_name, partition_key)
                logger.info(f"Creating partition {partition_name} for range {partition_key} to {next_key}")
                
                # Check if partition exists
                check_sql = text("""
                    SELECT EXISTS (
                        SELECT FROM pg_tables
                        WHERE schemaname = 'data_playground' AND tablename = :partition_name
                    )
                """)
                result = await connection.execute(check_sql, {"partition_name": partition_name})
                exists = result.scalar()
                
                if not exists:
                    # Create partition if it doesn't exist
                    create_sql = text(f"""
                        CREATE TABLE IF NOT EXISTS data_playground.{partition_name}
                        PARTITION OF data_playground.{table_name}
                        FOR VALUES FROM ('{partition_key}') TO ('{next_key}')
                    """)
                    await connection.execute(create_sql)
                    logger.info(f"Created new partition {partition_name}")
                else:
                    logger.info(f"Partition {partition_name} already exists")
                
                # Move to next interval
                current_time = next_time
                
            except Exception as e:
                logger.error(f"Error creating partition for {table_name}: {str(e)}")
                raise

        return True

    except Exception as e:
        logger.error(f"Error in check_and_create_partition for {table_name}: {str(e)}")
        raise

async def initialize_table(connection: AsyncConnection, tables: Union[str, List[str]], start_range: datetime = None, end_range: datetime = None):
    """Initialize partitions for one or more tables"""
    try:
        # Convert single table to list
        if isinstance(tables, str):
            tables = [tables]
            
        # Default to 365 days in past to 365 days in future
        now = datetime.utcnow()
        if start_range is None:
            start_range = now - timedelta(days=365)
        if end_range is None:
            end_range = now + timedelta(days=365)
            
        logger.info(f"Initializing partitions for tables: {tables}")
        logger.info(f"Time range: {start_range} to {end_range}")
        
        results = {}
        for table in tables:
            try:
                success = await check_and_create_partition(connection, table, start_range, end_range)
                results[table] = "Success" if success else "Failed"
                logger.info(f"Partition initialization for {table}: {results[table]}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error initializing table {table}: {error_msg}")
                results[table] = f"Error: {error_msg}"
                
        return results
        
    except Exception as e:
        logger.error(f"Error in initialize_table: {str(e)}")
        raise