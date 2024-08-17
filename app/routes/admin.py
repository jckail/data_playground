from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from ..utils.generate_fake_data import generate_fake_data
from datetime import datetime, timedelta, date
import pytz
from sqlalchemy import text
import httpx
from ..models import EventPropensity, FakeHelper, User, Shop
import time
from ..schemas import FakeDataQuery, UserSnapshot, UserSnapshotResponse, ShopSnapshot, ShopSnapshotResponse
from ..database import get_db
from app.utils.helpers import post_request, BASE_URL
import logging

# Set up the logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

async def run_rollup(current_date, endpoint):
    event_time = current_date.isoformat()
    payload = {"event_time": current_date.isoformat()}
    url = f"{BASE_URL}/admin/{endpoint}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await post_request(
                client,
                url,
                payload,
                f"Failed to run  {url} @ {event_time}",
            )
        logger.info(f"Rollup for {endpoint} completed successfully at {event_time}")
        return response
    except Exception as e:
        logger.error(f"Error during rollup for {endpoint} at {event_time}: {str(e)}")
        raise

@router.post("/create_rollups")
async def create_rollups(
    background_tasks: BackgroundTasks, 
    start_date: datetime = None, 
    end_date: datetime = None, 
    db: Session = Depends(get_db)
):
    try:
        dates = []
        
        # If both start_date and end_date are not provided, query all possible dates
        if start_date is None or end_date is None:
            logger.info("No start_date or end_date provided. Fetching all possible dates from global_events.")
            date_query = text("""
                SELECT DISTINCT date(event_time) AS event_date
                FROM global_events
                ORDER BY event_date
            """)
            result = db.execute(date_query)
            dates = [row.event_date for row in result.fetchall()]
            
            if not dates:
                raise HTTPException(status_code=404, detail="No dates found in global_events")
            
            if not start_date:
                start_date = dates[0]
            if not end_date:
                end_date = dates[-1]
            logger.info(f"Processing rollups for dates from {start_date} to {end_date}")

        # If either start_date or end_date is provided, or we have fetched the dates
        if start_date is not None and end_date is not None:
            if not dates:
                dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        
        for current_date in dates:
            background_tasks.add_task(run_rollup, current_date, "user_snapshot")
            background_tasks.add_task(run_rollup, current_date, "shop_snapshot")

        return {"message": f"Rollups creation tasks have been initiated between {start_date} and {end_date}"}
    
    except Exception as e:
        logger.error(f"Failed to create rollups: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create rollups: {str(e)}")





async def run_data_generation(
    start_date: datetime,
    end_date: datetime,
    max_fake_users_per_day: int,
    max_user_churn: float,
    max_first_shop_creation_percentage: float,
    max_multiple_shop_creation_percentage: float,
    max_shop_churn: float,
    semaphore: int = 250,
):
    logger.info(f"Starting data generation from {start_date} to {end_date} with max_fake_users_per_day={max_fake_users_per_day}")

    ep = EventPropensity(
        max_fake_users_per_day,
        max_user_churn,
        max_first_shop_creation_percentage,
        max_multiple_shop_creation_percentage,
        max_shop_churn,
    )
    fh = FakeHelper(semaphore=semaphore)
    z = {}
    start_time = time.time()

    # Initialize totals
    total_users_created = 0
    total_users_deactivated = 0
    total_shops_created = 0
    total_shops_deleted = 0

    try:
        for i in range((end_date - start_date).days + 1):
            current_date = start_date + timedelta(days=i)
            logger.debug(f"Generating fake data for {current_date}")

            # Reset daily counts
            fh.reset_daily_counts()

            # Run the daily data generation process
            z[current_date] = await generate_fake_data(current_date, z, ep, fh)

            # Accumulate daily totals into the overall totals
            total_users_created += fh.daily_users_created
            total_users_deactivated += fh.daily_users_deactivated
            total_shops_created += fh.daily_shops_created
            total_shops_deleted += fh.daily_shops_deleted

            logger.debug(f"Day {current_date}: Users Created = {fh.daily_users_created}, Users Deactivated = {fh.daily_users_deactivated}, Shops Created = {fh.daily_shops_created}, Shops Deleted = {fh.daily_shops_deleted}")

    except Exception as e:
        logger.error(f"Error during data generation: {str(e)}")
        raise

    # Calculate the total runtime
    end_time = time.time()
    run_time = end_time - start_time

    # Create the final summary
    summary_dict = {
        "total_users_created": total_users_created,
        "total_users_deactivated": total_users_deactivated,
        "total_active_users": len(fh.users),  # Active users left in the system
        "total_shops_created": total_shops_created,
        "total_shops_deleted": total_shops_deleted,
        "total_active_shops": len(fh.shops),  # Active shops left in the system
        "total_days": (end_date - start_date).days + 1,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "run_time": round(run_time, 4),
    }

    logger.info(f"Data generation complete. Summary: {summary_dict}")

    return summary_dict

@router.post("/generate_fake_data")
async def trigger_fake_data_generation(
    fdq: FakeDataQuery,  # Use the schema defined in schemas.py
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    logger.info(f"Triggering fake data generation for date range {fdq.start_date} to {fdq.end_date}")

    yesterday = datetime.now(pytz.utc).date() - timedelta(minutes=1)

    if fdq.start_date.date() > yesterday:
        logger.warning(f"Start date {fdq.start_date} cannot be later than yesterday {yesterday}")
        raise HTTPException(
            status_code=400, detail="Start date cannot be later than yesterday"
        )

    try:
        result_summary = await run_data_generation(
            fdq.start_date,
            fdq.end_date,
            fdq.max_fake_users_per_day,
            fdq.max_user_churn,
            fdq.max_first_shop_creation_percentage,
            fdq.max_multiple_shop_creation_percentage,
            fdq.max_shop_churn,
        )
    except Exception as e:
        logger.error(f"Data generation failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Data generation failed: {str(e)}"
        )

    logger.info(f"Fake data generation completed successfully for {fdq.start_date} to {fdq.end_date}")
    
    return {
        "message": "Fake data generation completed",
        "start_date": fdq.start_date.isoformat(),
        "end_date": fdq.end_date.isoformat(),
        "summary": result_summary,
    }

@router.post("/user_snapshot", response_model=UserSnapshotResponse)
def user_snapshot(
    snapshot: UserSnapshot, db: Session = Depends(get_db)
):
    logger.info("Starting user snapshot generation")

    try:
        event_time = snapshot.event_time or datetime.utcnow().replace(
            tzinfo=pytz.UTC
        )
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

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

        res = db.execute(text(query))
        rows = res.fetchall()
        logger.info(f"Fetched {len(rows)} rows for user snapshot")

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
            logger.debug(f"Processing row {i+1}/{len(rows)}: {row}")
            existing_record = db.query(User).filter(User.id == row.id).first()

            new_record = User.validate_partition(
                db=db,
                id=row.id,
                email=row.email,
                status=row.status,
                created_time=row.created_time,
                deactivated_time=row.deactivated_time,
                event_time=event_time,
            )

            if existing_record:
                logger.debug(f"Updating existing user record with ID: {row.id}")
                res = db.execute(
                    update_query,
                    {
                        "id": new_record.id,
                        "email": new_record.email,
                        "status": new_record.status,
                        "created_time": new_record.created_time,
                        "deactivated_time": new_record.deactivated_time,
                        "partition_key": new_record.partition_key,
                        "event_time": new_record.event_time, 
                    }
                )
            else:
                logger.debug(f"Creating new user record with ID: {row.id}")
                db.add(new_record)

        db.commit()

        users_processed = get_users_processed_count(db, partition_key)
        logger.info(f"User snapshot generation complete for partition_key {partition_key}. Users processed: {users_processed}")

        return UserSnapshotResponse(
            event_time=event_time,
            event_type="user_snapshot",
            event_metadata={"users_processed": users_processed},
        )

    except Exception as e:
        db.rollback()
        logger.error(f"User snapshot failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"User snapshot failed: {str(e)}"
        )

def get_users_processed_count(db: Session, partition_key: date) -> int:
    try:
        result = db.execute(
            text(f"SELECT COUNT(*) FROM users WHERE partition_key::date = '{partition_key}'::date"),
            {"partition_key": partition_key},
        ).scalar()
        logger.debug(f"Users processed count for {partition_key}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error counting processed users: {str(e)}")
        raise

@router.post("/shop_snapshot", response_model=ShopSnapshotResponse)
def shop_snapshot(
    snapshot: ShopSnapshot, db: Session = Depends(get_db)
):
    logger.info("Starting shop snapshot generation")

    try:
        event_time = snapshot.event_time or datetime.utcnow().replace(
            tzinfo=pytz.UTC
        )
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

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

        res = db.execute(text(query))
        rows = res.fetchall()
        logger.info(f"Fetched {len(rows)} rows for shop snapshot")

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

        for row in rows:
            logger.debug(f"Processing shop record: {row}")
            existing_record = db.query(Shop).filter(Shop.id == row.id).first()

            new_record = Shop.validate_partition(
                db=db,
                id=row.id,
                shop_owner_id=row.shop_owner_id,
                shop_name=row.shop_name,
                status=row.status,
                created_time=row.created_time,
                deactivated_time=row.deactivated_time,
                event_time=event_time,
            )

            if existing_record:
                logger.debug(f"Updating existing shop record with ID: {row.id}")
                db.execute(
                    update_query,
                    {
                        "id": new_record.id,
                        "shop_owner_id": new_record.shop_owner_id,
                        "shop_name": new_record.shop_name,
                        "status": new_record.status,
                        "created_time": new_record.created_time,
                        "deactivated_time": new_record.deactivated_time,
                        "partition_key": new_record.partition_key,
                        "event_time": new_record.event_time, 
                    }
                )
            else:
                logger.debug(f"Creating new shop record with ID: {row.id}")
                db.add(new_record)

        db.commit()

        shops_processed = get_shops_processed_count(db, partition_key)
        logger.info(f"Shop snapshot generation complete for partition_key {partition_key}. Shops processed: {shops_processed}")

        return ShopSnapshotResponse(
            event_time=event_time,
            event_type="shop_snapshot",
            event_metadata={"shops_processed": shops_processed},
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Shop snapshot failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Shop snapshot failed: {str(e)}"
        )

def get_shops_processed_count(db: Session, partition_key: date) -> int:
    try:
        result = db.execute(
            text(f"SELECT COUNT(*) FROM shops WHERE partition_key::date = '{partition_key}'::date"),
            {"partition_key": partition_key},
        ).scalar()
        logger.debug(f"Shops processed count for {partition_key}: {result}")
        return result
    except Exception as e:
        logger.error(f"Error counting processed shops: {str(e)}")
        raise
