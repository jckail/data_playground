from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from .. import database
from ..utils.generate_fake_data import generate_fake_data
from datetime import datetime, timedelta
from pydantic import BaseModel
import pytz

router = APIRouter()

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_yesterday():
    return datetime.now(pytz.utc).date() - timedelta(days=1)


async def run_data_generation(db: Session, start_date: datetime, end_date: datetime):
    result = await generate_fake_data( start_date, end_date)
    print(f"Data generation complete. Results: {result}")



@router.post("/generate_fake_data")
async def trigger_fake_data_generation(date_range: DateRange, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    yesterday = get_yesterday()
    
    if date_range.start_date.date() > yesterday:
        raise HTTPException(status_code=400, detail="Start date cannot be later than yesterday")
    
    end_date = datetime.combine(yesterday, datetime.max.time()).replace(tzinfo=pytz.UTC)
    start_date = date_range.start_date.replace(tzinfo=pytz.UTC)
    
    background_tasks.add_task(run_data_generation, db, start_date, end_date)
    return {
        "message": "Fake data generation started in the background",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
