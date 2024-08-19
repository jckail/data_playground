from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..database import get_db
import logging
import pytz

from ..models import Shop
from ..schemas import ShopSnapshot, ShopSnapshotResponse
from .helpers import retry_with_backoff
from sqlalchemy.exc import OperationalError

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

@router.post("/shop_snapshot", response_model=ShopSnapshotResponse)
async def shop_snapshot(
    snapshot: ShopSnapshot, db: AsyncSession = Depends(get_db)
):
    logger.info("Starting shop snapshot generation")
    
    try:
        event_time = snapshot.event_time or datetime.utcnow().replace(tzinfo=pytz.UTC)
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

        rows = await fetch_shop_data(db, partition_key, previous_day)
        await process_shop_data(db, rows, partition_key, event_time)

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

@retry_with_backoff()
async def fetch_shop_data(db: AsyncSession, partition_key: datetime.date, previous_day: datetime.date):
    try:
        logger.info(f"Fetching shop data for partition_key {partition_key} and previous_day {previous_day}")

        query = f"""
            WITH base AS (
                SELECT 
                    event_metadata->>'shop_id' AS id,
                    event_metadata->>'shop_owner_id' AS shop_owner_id,
                    event_metadata->>'shop_name' AS shop_name,
                    event_time as created_time,
                    NULL as deactivated_time     
                FROM global_events
                WHERE event_type = 'user_shop_create'
                AND event_time::date = '{partition_key}'::date
                
                UNION ALL 
                
                SELECT 
                    event_metadata->>'shop_id' AS id,
                    event_metadata->>'shop_owner_id' AS shop_owner_id,
                    NULL as shop_name,
                    NULL as created_time,
                    event_time as deactivated_time     
                FROM global_events
                WHERE event_type = 'user_shop_delete'
                AND event_time::date = '{partition_key}'::date
                
                UNION ALL 
                
                SELECT 
                    id::text,
                    shop_owner_id::text,
                    shop_name,
                    created_time,
                    deactivated_time    
                FROM shops
                WHERE partition_key::date = '{previous_day}'::date

                UNION ALL 
                
                SELECT 
                    id::text,
                    shop_owner_id::text,
                    shop_name,
                    created_time,
                    deactivated_time    
                FROM shops
                WHERE partition_key::date = '{partition_key}'::date
            ),
            base2 AS (
                SELECT 
                    id,
                    shop_owner_id,
                    MAX(shop_name) AS shop_name,
                    MAX(created_time) AS created_time,
                    MAX(deactivated_time) AS deactivated_time   
                FROM base
                WHERE id IS NOT NULL
                AND shop_owner_id IS NOT NULL
                GROUP BY id, shop_owner_id  
            )
            SELECT 
                DISTINCT 
                id::uuid,
                shop_owner_id::uuid,
                shop_name,
                CASE WHEN deactivated_time IS NULL THEN TRUE ELSE FALSE END AS status,
                created_time,
                deactivated_time,
                '{partition_key}'::date as partition_key
            FROM base2
        """

        result = await db.execute(text(query))
        rows = result.fetchall()
        logger.info(f"Fetched {len(rows)} rows for shop snapshot")
        return rows

    except OperationalError as e:
        if "No space left on device" in str(e):
            logger.critical("Database is out of disk space. Please free up space immediately.")
            # You might want to trigger an alert here
            raise HTTPException(status_code=503, detail="Database is temporarily unavailable due to maintenance.")
        else:
            logger.error(f"Error fetching shop data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error fetching shop data: {str(e)}")

@retry_with_backoff()
async def process_shop_data(db: AsyncSession, rows, partition_key: datetime.date, event_time: datetime):
    try:
        logger.info(f"Processing {len(rows)} rows of shop data")

        update_query = text("""
            INSERT INTO shops (id, shop_owner_id, shop_name, status, created_time, deactivated_time, partition_key, event_time)
            VALUES (:id, :shop_owner_id, :shop_name, :status, :created_time, :deactivated_time, :partition_key, :event_time)
            ON CONFLICT (id, partition_key)
            DO UPDATE SET
                shop_owner_id = EXCLUDED.shop_owner_id,
                shop_name = COALESCE(EXCLUDED.shop_name, shops.shop_name),
                status = EXCLUDED.status,
                created_time = COALESCE(shops.created_time, EXCLUDED.created_time),
                deactivated_time = COALESCE(EXCLUDED.deactivated_time, shops.deactivated_time),
                event_time = EXCLUDED.event_time
            RETURNING id
        """)

        for i, row in enumerate(rows):
            try:
                logger.debug(f"Processing row {i+1}/{len(rows)}: {row}")

                new_record = await Shop.validate_partition(
                    db=db,
                    id=row.id,
                    shop_owner_id=row.shop_owner_id,
                    shop_name=row.shop_name,
                    status=row.status,
                    created_time=row.created_time,
                    deactivated_time=row.deactivated_time,
                    event_time=event_time,
                )

                partition_key_str = partition_key.isoformat()

                existing_record_query = await db.execute(
                    text("SELECT * FROM shops WHERE id = :id AND partition_key = :partition_key"),
                    {"id": new_record.id, "partition_key": partition_key_str}
                )
                existing_record = existing_record_query.fetchone()

                if existing_record:
                    logger.debug(f"Updating existing shop record with ID: {new_record.id}")
                    await db.execute(
                        update_query,
                        {
                            "id": new_record.id,
                            "shop_owner_id": new_record.shop_owner_id,
                            "shop_name": new_record.shop_name,
                            "status": new_record.status,
                            "created_time": new_record.created_time,
                            "deactivated_time": new_record.deactivated_time,
                            "partition_key": partition_key_str,
                            "event_time": new_record.event_time,
                        }
                    )
                else:
                    logger.debug(f"Creating new shop record with ID: {new_record.id}")
                    await db.execute(
                        text("""
                            INSERT INTO shops (id, shop_owner_id, shop_name, status, created_time, deactivated_time, partition_key, event_time)
                            VALUES (:id, :shop_owner_id, :shop_name, :status, :created_time, :deactivated_time, :partition_key, :event_time)
                        """),
                        {
                            "id": new_record.id,
                            "shop_owner_id": new_record.shop_owner_id,
                            "shop_name": new_record.shop_name,
                            "status": new_record.status,
                            "created_time": new_record.created_time,
                            "deactivated_time": new_record.deactivated_time,
                            "partition_key": partition_key_str,
                            "event_time": new_record.event_time,
                        }
                    )

            except Exception as row_error:
                logger.error(f"Error processing row {i+1}/{len(rows)}: {str(row_error)}")
                raise

        await db.commit()
        logger.info("Shop data processing and commit successful")

    except Exception as e:
        logger.error(f"Error processing shop data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing shop data: {str(e)}")

@retry_with_backoff()
async def get_shops_processed_count(db: AsyncSession, partition_key: datetime.date) -> int:
    try:
        logger.info(f"Counting shops processed for partition_key {partition_key}")
        
        # Convert the date to a string in 'YYYY-MM-DD' format
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
        raise HTTPException(status_code=500, detail=f"Error counting processed shops: {str(e)}")