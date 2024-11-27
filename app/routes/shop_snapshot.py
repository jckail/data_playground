from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from ..database import get_db
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import Shop
from ..schemas import ShopSnapshot, ShopSnapshotResponse
from .helpers import retry_with_backoff

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def generate_partition_name(tablename, partition_key):
    return f"{tablename}_p_{partition_key.replace('-', '_')}"

@router.post("/shop_snapshot", response_model=ShopSnapshotResponse)
async def shop_snapshot(
    snapshot: ShopSnapshot, db: AsyncSession = Depends(get_db)
):
    logger.info("Starting shop snapshot generation")
    
    try:
        event_time = snapshot.event_time or datetime.utcnow()
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

        # Delete the current day's partition from shops
        await delete_current_partition(db, partition_key)
        
        # Ensure partition exists
        await ensure_partition_exists(db, partition_key)

        # Fetch shop data and insert into shops table
        await fetch_and_insert_shop_data(db, partition_key, previous_day, event_time)

        shops_processed = await get_shops_processed_count(db, partition_key)
        logger.info(f"Shop snapshot generation complete for partition_key {partition_key}. Shops processed: {shops_processed}")

        return ShopSnapshotResponse(
            event_time=event_time,
            event_type="shop_snapshot",
            event_metadata={"shops_processed": shops_processed},
        )

    except Exception as e:
        logger.error(f"Shop snapshot failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Shop snapshot failed: {str(e)}")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def delete_current_partition(db: AsyncSession, partition_key: date):
    try:
        partition_key_str = partition_key.strftime('%Y-%m-%d')
        logger.info(f"Deleting current day's partition for {partition_key_str}")
        
        delete_query = text("DELETE FROM shops WHERE partition_key = :partition_key")
        await db.execute(delete_query, {"partition_key": partition_key_str})
        await db.commit()
        
        logger.info(f"Deleted partition for {partition_key_str}")

    except Exception as e:
        logger.error(f"Error deleting partition for {partition_key_str}: {str(e)}")
        await db.rollback()
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def ensure_partition_exists(db: AsyncSession, partition_key: date):
    partition_name = generate_partition_name("shops", partition_key.strftime('%Y_%m_%d')).lower()
    start_date = partition_key.strftime('%Y-%m-%d')
    end_date = (partition_key + timedelta(days=1)).strftime('%Y-%m-%d')
    
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF shops
    FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """
    
    try:
        await db.execute(text(create_query))
        await db.commit()
        logger.info(f"Ensured partition {partition_name} exists")
    except ProgrammingError as e:
        if 'already exists' in str(e):
            logger.info(f"Partition {partition_name} already exists")
        else:
            logger.error(f"Error ensuring partition {partition_name} exists: {str(e)}")
            await db.rollback()
            raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def fetch_and_insert_shop_data(db: AsyncSession, partition_key: date, previous_day: date, event_time: datetime):
    try:
        logger.info(f"Fetching and inserting shop data for partition_key {partition_key} and previous_day {previous_day}")

        query = f"""
        INSERT INTO shops (id, shop_owner_id, shop_name, status, created_time, deactivated_time, partition_key, event_time)
        WITH base AS (
            SELECT 
                (event_metadata->>'shop_id')::uuid AS id,
                (event_metadata->>'shop_owner_id')::uuid AS shop_owner_id,
                event_metadata->>'shop_name' AS shop_name,
                event_time::timestamp as created_time,
                NULL::timestamp as deactivated_time,
                event_time::timestamp
            FROM global_events
            WHERE event_type = 'user_shop_create'
            AND event_time::date = '{partition_key}'

            UNION ALL 
                 
            SELECT 
                (event_metadata->>'shop_id')::uuid AS id,
                (event_metadata->>'shop_owner_id')::uuid AS shop_owner_id,
                event_metadata->>'shop_name' AS shop_name,
                NULL::timestamp as created_time,
                event_time::timestamp as deactivated_time,
                event_time::timestamp
            FROM global_events
            WHERE event_type = 'user_shop_delete'
            AND event_time::date = '{partition_key}'

            UNION ALL 

            SELECT 
                id,
                shop_owner_id,
                shop_name,
                created_time::timestamp,
                deactivated_time::timestamp,
                event_time::timestamp
            FROM shops
            WHERE partition_key::date = '{previous_day}'
        ),
        base2 AS (
            SELECT 
                id,
                shop_owner_id,
                MAX(shop_name) AS shop_name,
                MAX(created_time) AS created_time,
                MAX(deactivated_time) AS deactivated_time,
                MAX(event_time) AS event_time   
            FROM base
            WHERE id IS NOT NULL
            AND shop_owner_id IS NOT NULL
            GROUP BY id, shop_owner_id  
        )
        SELECT 
            DISTINCT 
            id,
            shop_owner_id,
            shop_name,
            CASE WHEN deactivated_time IS NULL THEN TRUE ELSE FALSE END AS status,
            created_time,
            deactivated_time,
            '{partition_key}' AS partition_key,
            event_time 
        FROM base2
        """

        result = await db.execute(text(query))
        logger.info(f"Data insert operation successful, preparing to commit the transaction.")

        # Commit the transaction
        await db.commit()
        logger.info("Transaction committed successfully.")

        
        logger.info("Shop data inserted successfully")

    except Exception as e:
        logger.error(f"Error fetching and inserting shop data: {str(e)}")
        await db.rollback()
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def get_shops_processed_count(db: AsyncSession, partition_key: date) -> int:
    try:
        logger.info(f"Counting shops processed for partition_key {partition_key}")
        
        partition_key_str = partition_key.strftime('%Y-%m-%d')
        
        result = await db.execute(
            text("SELECT COUNT(*) FROM shops WHERE partition_key = :partition_key"),
            {"partition_key": partition_key_str},
        )
        count = result.scalar()
        logger.debug(f"Shops processed count for {partition_key}: {count}")
        return count

    except Exception as e:
        logger.error(f"Error counting processed shops: {str(e)}")
        raise