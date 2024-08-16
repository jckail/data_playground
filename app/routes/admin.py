from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database
from ..utils.generate_fake_data import generate_fake_data
from datetime import datetime, timedelta, date
import pytz
from sqlalchemy import text
from dateutil.parser import parse
from ..models import EventPropensity, FakeHelper
import logging
import time


router = APIRouter()


# Dependency to get the database session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def run_data_generation(
    start_date: datetime,
    end_date: datetime,
    max_fake_users_per_day: int,
    max_user_churn: float,
    max_first_shop_creation_percentage: float,
    max_multiple_shop_creation_percentage: float,
    max_shop_churn: float,
    semaphore: int = 20,
):

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
    for i in range((end_date - start_date).days + 1):
        current_date = start_date + timedelta(days=i)
        z = await generate_fake_data(current_date, z, ep, fh)


    # Calculate the total runtime
    end_time = time.time()
    run_time = end_time - start_time

    summary_dict = {
            "total_users_created": sum(z[current_date].daily_users_created for current_date in z),
            "total_users_deactivated": sum(z[current_date].daily_users_deactivated for current_date in z),
            "total_active_users": len(fh.users),
            "total_shops_created": sum(z[current_date].daily_shops_created for current_date in z),
            "total_shops_deleted": sum(z[current_date].daily_shops_deleted for current_date in z),
            "total_active_shops": len(fh.shops),
            "total_days": (end_date - start_date).days + 1,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "run_time": round(run_time,4),
        }

    if summary_dict is None:
        raise HTTPException(
            status_code=500,
            detail="Data generation failed: No data was returned from generate_fake_data",
        )

    print(f"Data generation complete. Summary: {summary_dict}")

    return summary_dict


@router.post("/generate_fake_data")
async def trigger_fake_data_generation(
    fdq: schemas.FakeDataQuery,  # Use the schema defined in schemas.py
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    yesterday = datetime.now(pytz.utc).date() - timedelta(days=1)

    if fdq.start_date.date() > yesterday:
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
        raise HTTPException(
            status_code=500, detail=f"Data generation failed: {e}"
        )

    return {
        "message": "Fake data generation completed",
        "start_date": fdq.start_date.isoformat(),
        "end_date": fdq.end_date.isoformat(),
        "summary": result_summary,
    }



##TODO: Implement the user_snapshot endpoint
## THIS IS BROKEN BECAUSE OF THE WAY create_partition_if_not_exists is implemented
## create_partition_if_not_exists should be on each model in "generate_partition_key_if_not_exists"
## and "Generate partition keysSSSS if not exists


@router.post("/user_snapshot", response_model=schemas.UserSnapshotResponse)
def user_snapshot(
    snapshot: schemas.UserSnapshot, db: Session = Depends(get_db)
):
    try:
        # Use the event_time from the schema, or default to current time
        event_time = snapshot.event_time or datetime.utcnow().replace(
            tzinfo=pytz.UTC
        )

        # Partition key based on the event_time
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

        # Paths: 
        # format: yyyy-mm-dd
        # Timestamp
        # Date --> STR


        # Debugging: Ensure these are date objects
        print(f"partition_key: {partition_key}, type: {type(partition_key)}")
        print(f"previous_day: {previous_day}, type: {type(previous_day)}")





        # Process user creation and deletion events
        process_user_events(db, partition_key, previous_day)
        db.commit()
        # Commit the transaction to ensure data is saved
        

        # Return the response after processing
        users_processed = get_users_processed_count(db, partition_key)
        db.commit()
        
        return schemas.UserSnapshotResponse(
            event_time=event_time,
            event_type="user_snapshot",
            event_metadata={
                "snapshot_date": str(partition_key),
                "users_processed": users_processed,
            },
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"User snapshot failed: {e}"
        )



def process_user_events(db: Session, partition_key: date, previous_day: date):
    # Query and process creation events
    get_user_events(
        db, partition_key, previous_day
    )



def get_user_events(db: Session, partition_key: str, previous_day: str):


    query = text(
        """
        INSERT INTO users (id, email, status, created_time, deactivated_time, partition_key)
        WITH base AS (
            SELECT 
                event_metadata->>'user_id' AS id,
                event_metadata->>'email' AS email,
                event_time as created_time,
                NULL as deactivated_time     
            FROM global_events
            WHERE event_type = 'user_account_creation'
            AND event_time::date = :partition_key
            
            UNION ALL 
            
            SELECT 
                event_metadata->>'user_id' AS id,
                event_metadata->>'email' AS email,
                NULL as created_time,
                event_time as deactivated_time     
            FROM global_events
            WHERE event_type = 'user_deactivate_account'
            AND event_time::date = :partition_key
            
            UNION ALL 
            
            SELECT 
                id::text,
                email,
                created_time,
                deactivated_time    
            FROM users
            WHERE partition_key = :previous_day
        ),
        base2 AS (
            SELECT 
                id,
                email,
                MAX(created_time) AS created_time,
                MAX(deactivated_time) AS deactivated_time   
            FROM base
            GROUP BY id, email
        )
        SELECT 
            DISTINCT 
            id::uuid,
            email,
            CASE WHEN deactivated_time IS NULL THEN TRUE ELSE FALSE END AS status,
            created_time,
            deactivated_time,
            :partition_key partition_key
        FROM base2
        """
    )
    db.execute(
        query,
        {
            
            "previous_day": previous_day,
            "partition_key": partition_key,
        }
    )

def get_users_processed_count(db: Session, partition_key: date) -> int:
    result = db.execute(
        text("SELECT COUNT(*) FROM users WHERE partition_key = :partition_key"),
        {"partition_key": partition_key},
    ).scalar()
    return result