from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from .. import database, schemas  # Import the schemas module
from ..utils.generate_fake_data import generate_fake_data
from datetime import datetime, timedelta
import pytz
from sqlalchemy import text

from ..models import EventPropensity, FakeHelper

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
    max_first_shop_creation_percentage : float, 
    max_multiple_shop_creation_percentage : float, 
    max_shop_churn: float,
    semaphore: int = 10
):
    
    ep = EventPropensity(
        max_fake_users_per_day,
        max_user_churn,
        max_first_shop_creation_percentage,
        max_multiple_shop_creation_percentage,
        max_shop_churn
    )
    fh = FakeHelper(semaphore=semaphore)


    summary_dict = await generate_fake_data(
        start_date, 
        end_date, 
        ep, 
        fh
    )
    
    if summary_dict is None:
        raise HTTPException(
            status_code=500, 
            detail="Data generation failed: No data was returned from generate_fake_data"
        )

    print(f"Data generation complete. Summary: {summary_dict}")
    
    return summary_dict

@router.post("/generate_fake_data")
async def trigger_fake_data_generation(
    fdq: schemas.FakeDataQuery,  # Use the schema defined in schemas.py
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    yesterday = datetime.now(pytz.utc).date() - timedelta(days=1)
    
    if fdq.start_date.date() > yesterday:
        raise HTTPException(status_code=400, detail="Start date cannot be later than yesterday")
    
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
        raise HTTPException(status_code=500, detail=f"Data generation failed: {e}")
    
    return {
        "message": "Fake data generation completed",
        "start_date": fdq.start_date.isoformat(),
        "end_date": fdq.end_date.isoformat(),
        "summary": result_summary,
    }



@router.post("/user_snapshot")
def user_snapshot(snapshot_date: datetime, db: Session = Depends(get_db)):
    try:
        # Partition key based on the snapshot_date
        partition_key = snapshot_date.date()
        previous_day = partition_key - timedelta(days=1)

        # Query to get all user creation events for the specified date and previous day
        creation_query = text("""
            SELECT 
                event_metadata->>'user_id' AS user_id,
                event_time
            FROM global_events
            WHERE event_type = 'user_account_creation'
            AND event_time::date IN (:snapshot_date, :previous_day)
        """)

        creation_events = db.execute(creation_query, {"snapshot_date": partition_key, "previous_day": previous_day}).fetchall()

        # Query to get all user deletion events for the specified date and previous day
        deletion_query = text("""
            SELECT 
                event_metadata->>'user_id' AS user_id,
                event_time
            FROM global_events
            WHERE event_type = 'user_delete_account'
            AND event_time::date IN (:snapshot_date, :previous_day)
        """)

        deletion_events = db.execute(deletion_query, {"snapshot_date": partition_key, "previous_day": previous_day}).fetchall()

        # Process creation events
        for event in creation_events:
            db.execute(
                text("""
                    INSERT INTO users (id, status, created_time, deactivated_time, partition_key)
                    VALUES (:user_id, TRUE, :created_time, NULL, :partition_key)
                    ON CONFLICT (id, partition_key) DO NOTHING
                """),
                {"user_id": event.user_id, "created_time": event.event_time, "partition_key": partition_key}
            )

        # Process deletion events
        for event in deletion_events:
            db.execute(
                text("""
                    UPDATE users 
                    SET status = FALSE, deactivated_time = :deactivated_time
                    WHERE id = :user_id AND partition_key = :partition_key
                """),
                {"user_id": event.user_id, "deactivated_time": event.event_time, "partition_key": partition_key}
            )

        db.commit()

        return {"message": "User snapshot completed successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"User snapshot failed: {e}")