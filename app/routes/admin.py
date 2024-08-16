from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from .. import database, schemas  # Import the schemas module
from ..utils.generate_fake_data import generate_fake_data
from datetime import datetime, timedelta
import pytz

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
