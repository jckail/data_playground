from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..database import get_db
import logging

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

@router.post("/user_snapshot", response_model=UserSnapshotResponse)
async def user_snapshot(
    snapshot: UserSnapshot, db: AsyncSession = Depends(get_db)
):
    logger.info("Starting user snapshot generation")
    
    try:
        event_time = snapshot.event_time or datetime.utcnow()
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

        rows = await fetch_user_data(db, partition_key, previous_day)
        await process_user_data(db, rows, partition_key, event_time)

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

@retry_with_backoff()
async def fetch_user_data(db: AsyncSession, partition_key: datetime.date, previous_day: datetime.date):
    try:
        logger.info(f"Fetching user data for partition_key {partition_key} and previous_day {previous_day}")

        query = f"""
            WITH base AS (
                SELECT 
                    event_metadata->>'user_id' AS id,
                    event_metadata->>'email' AS email,
                    event_time as created_time,
                    NULL as deactivated_time     
                FROM global_events
                WHERE event_type = 'user_account_creation'
                AND event_time::date = '{partition_key}'::date
                
                UNION ALL 
                
                SELECT 
                    event_metadata->>'user_id' AS id,
                    event_metadata->>'email' AS email,
                    NULL as created_time,
                    event_time as deactivated_time     
                FROM global_events
                WHERE event_type = 'user_delete_account'
                AND event_time::date = '{partition_key}'::date
                
                UNION ALL 
                
                SELECT 
                    id::text,
                    email,
                    created_time,
                    deactivated_time    
                FROM users
                WHERE partition_key::date = '{previous_day}'::date

                UNION ALL 
                
                SELECT 
                    id::text,
                    email,
                    created_time,
                    deactivated_time    
                FROM users
                WHERE partition_key::date = '{partition_key}'::date
            ),
            base2 AS (
                SELECT 
                    id,
                    email,
                    MAX(created_time) AS created_time,
                    MAX(deactivated_time) AS deactivated_time   
                FROM base
                WHERE id is not null
                AND email is not null
                GROUP BY id, email  
            )
            SELECT 
                DISTINCT 
                id::uuid,
                email,
                CASE WHEN deactivated_time IS NULL THEN TRUE ELSE FALSE END AS status,
                created_time,
                deactivated_time,
                '{partition_key}'::date AS partition_key
            FROM base2
        """

        result = await db.execute(text(query))
        rows = result.fetchall()  # Note: fetchall() is not awaited because it returns a list, not a coroutine
        logger.info(f"Fetched {len(rows)} rows for user snapshot")
        return rows

    except Exception as e:
        logger.error(f"Error fetching user data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching user data: {str(e)}")

async def process_user_data(db: AsyncSession, rows, partition_key: datetime.date, event_time: datetime):
    try:
        logger.info(f"Processing {len(rows)} rows of user data")

        update_query = text("""
            INSERT INTO users (id, email, status, created_time, deactivated_time, partition_key, event_time)
            VALUES (:id, :email, :status, :created_time, :deactivated_time, :partition_key, :event_time)
            ON CONFLICT (id, partition_key)
            DO UPDATE SET
                email = EXCLUDED.email,
                status = EXCLUDED.status,
                created_time = COALESCE(users.created_time, EXCLUDED.created_time),
                deactivated_time = COALESCE(EXCLUDED.deactivated_time, users.deactivated_time),
                event_time = EXCLUDED.event_time
            RETURNING id
        """)

        for i, row in enumerate(rows):
            try:
                logger.debug(f"Processing row {i+1}/{len(rows)}: {row}")

                # Await the `validate_partition` coroutine
                new_record = await User.validate_partition(
                    db=db,
                    id=row.id,
                    email=row.email,
                    status=row.status,
                    created_time=row.created_time,
                    deactivated_time=row.deactivated_time,
                    event_time=event_time,
                )

                # Convert partition_key to string
                partition_key_str = partition_key.isoformat()

                existing_record_query = await db.execute(
                    text("SELECT * FROM users WHERE id = :id AND partition_key = :partition_key"),
                    {"id": new_record.id, "partition_key": partition_key_str}
                )
                existing_record = existing_record_query.fetchone()

                if existing_record:
                    logger.debug(f"Updating existing user record with ID: {new_record.id}")
                    await db.execute(
                        update_query,
                        {
                            "id": new_record.id,
                            "email": new_record.email,
                            "status": new_record.status,
                            "created_time": new_record.created_time,
                            "deactivated_time": new_record.deactivated_time,
                            "partition_key": partition_key_str,
                            "event_time": new_record.event_time,
                        }
                    )
                else:
                    logger.debug(f"Creating new user record with ID: {new_record.id}")
                    await db.execute(
                        text("""
                            INSERT INTO users (id, email, status, created_time, deactivated_time, partition_key, event_time)
                            VALUES (:id, :email, :status, :created_time, :deactivated_time, :partition_key, :event_time)
                        """),
                        {
                            "id": new_record.id,
                            "email": new_record.email,
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
        logger.info("User data processing and commit successful")

    except Exception as e:
        logger.error(f"Error processing user data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing user data: {str(e)}")

@retry_with_backoff()
async def get_users_processed_count(db: AsyncSession, partition_key: datetime.date) -> int:
    try:
        logger.info(f"Counting users processed for partition_key {partition_key}")
        
        # Convert the date to a string in 'YYYY-MM-DD' format
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
        raise HTTPException(status_code=500, detail=f"Error counting processed users: {str(e)}")