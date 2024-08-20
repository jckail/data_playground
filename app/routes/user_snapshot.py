from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from ..database import get_db
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import User
from ..schemas import UserSnapshot, UserSnapshotResponse
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

@router.post("/user_snapshot", response_model=UserSnapshotResponse)
async def user_snapshot(
    snapshot: UserSnapshot, db: AsyncSession = Depends(get_db)
):
    logger.info("Starting user snapshot generation")
    
    try:
        event_time = snapshot.event_time or datetime.utcnow()
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

        # Delete the current day's partition from users
        await delete_current_partition(db, partition_key)

        # Ensure partition exists
        await ensure_partition_exists(db, partition_key)

        # Fetch user data and insert into users table
        await fetch_and_insert_user_data(db, partition_key, previous_day, event_time)

        users_processed = await get_users_processed_count(db, partition_key)
        logger.info(f"User snapshot generation complete for partition_key {partition_key}. Users processed: {users_processed}")

        return UserSnapshotResponse(
            event_time=event_time,
            event_type="user_snapshot",
            event_metadata={"users_processed": users_processed},
        )

    except Exception as e:
        logger.error(f"User snapshot failed: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"User snapshot failed: {str(e)}")


async def delete_current_partition(db: AsyncSession, partition_key: date):
    try:
        partition_key_str = partition_key.strftime('%Y-%m-%d')
        logger.info(f"Deleting current day's partition for {partition_key_str}")
        
        delete_query = text("DELETE FROM users WHERE partition_key = :partition_key")
        await db.execute(delete_query, {"partition_key": partition_key_str})
        await db.commit()
        
        logger.info(f"Deleted partition for {partition_key_str}")

    except Exception as e:
        logger.error(f"Error deleting partition for {partition_key_str}: {str(e)}")
        await db.rollback()
        raise


async def ensure_partition_exists(db: AsyncSession, partition_key: date):
    partition_name = generate_partition_name("users", partition_key.strftime('%Y_%m_%d')).lower()
    start_date = partition_key.strftime('%Y-%m-%d')
    end_date = (partition_key + timedelta(days=1)).strftime('%Y-%m-%d')
    
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF users
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


async def fetch_and_insert_user_data(db: AsyncSession, partition_key: date, previous_day: date, event_time: datetime):
    try:
        logger.info(f"Fetching and inserting user data for partition_key {partition_key} and previous_day {previous_day}")

        query = f"""
            INSERT INTO users (id, email, status, created_time, deactivated_time, partition_key, event_time)
            WITH base AS (
                SELECT 
                    event_metadata->>'user_id' AS id,
                    event_metadata->>'email' AS email,
                    event_time as created_time,
                    NULL as deactivated_time,
                    event_time::timestamp
                FROM global_events
                WHERE event_type = 'user_account_creation'
                AND event_time::date = '{partition_key}'
            
                UNION ALL 
            
                SELECT 
                    event_metadata->>'user_id' AS id,
                    event_metadata->>'email' AS email,
                    NULL as created_time,
                    event_time as deactivated_time,
                    event_time::timestamp
                FROM global_events
                WHERE event_type = 'user_delete_account'
                AND event_time::date = '{partition_key}'
            
                UNION ALL 
            
                SELECT 
                    id::text,
                    email,
                    created_time,
                    deactivated_time,
                    event_time::timestamp
                FROM users
                WHERE partition_key::date = '{previous_day}'
            ),
            base2 AS (
                SELECT 
                    id,
                    email,
                    MAX(created_time) AS created_time,
                    MAX(deactivated_time) AS deactivated_time,
                    MAX(event_time) AS event_time
                FROM base
                WHERE id IS NOT NULL
                AND email IS NOT NULL
                GROUP BY id, email
            )
            SELECT 
                DISTINCT 
                id::uuid,
                email,
                CASE WHEN deactivated_time IS NULL THEN TRUE ELSE FALSE END AS status,
                created_time,
                deactivated_time,
                '{partition_key}' AS partition_key,
                event_time
            FROM base2
        """

        await db.execute(text(query))
        await db.commit()
        
        logger.info("User data inserted successfully")

    except Exception as e:
        logger.error(f"Error fetching and inserting user data: {str(e)}")
        await db.rollback()
        raise


async def get_users_processed_count(db: AsyncSession, partition_key: date) -> int:
    try:
        logger.info(f"Counting users processed for partition_key {partition_key}")
        
        partition_key_str = partition_key.strftime('%Y-%m-%d')
        
        result = await db.execute(
            text("SELECT COUNT(*) FROM users WHERE partition_key = :partition_key"),
            {"partition_key": partition_key_str},
        )
        count = result.scalar()
        logger.debug(f"Users processed count for {partition_key}: {count}")
        return count

    except Exception as e:
        logger.error(f"Error counting processed users: {str(e)}")
        raise