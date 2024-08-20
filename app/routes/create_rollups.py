from datetime import datetime, timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..database import get_db
import logging
from app.utils.helpers import post_request, BASE_URL
import httpx
from sqlalchemy.orm import Session
from ..utils.generate_fake_data import generate_fake_data
from datetime import  date
import pytz


from ..models import EventPropensity, FakeHelper, User, Shop
import time
from ..schemas import FakeDataQuery, UserSnapshot, UserSnapshotResponse, ShopSnapshot, ShopSnapshotResponse
from ..database import get_db






router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

async def run_rollup(current_date, endpoint):
    event_time = current_date.isoformat()
    payload = {"event_time": event_time}
    url = f"{BASE_URL}/{endpoint}"
    
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
    db: AsyncSession = Depends(get_db)
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
            result = await db.execute(date_query)
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



# @router.post("/generate_fake_data")
# async def trigger_fake_data_generation(
#     fdq: FakeDataQuery,  # Use the schema defined in schemas.py
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
# ):
#     logger.info(f"Triggering fake data generation for date range {fdq.start_date} to {fdq.end_date}")

#     yesterday = datetime.now(pytz.utc).date() - timedelta(minutes=1)

#     if fdq.start_date.date() > yesterday:
#         logger.warning(f"Start date {fdq.start_date} cannot be later than yesterday {yesterday}")
#         raise HTTPException(
#             status_code=400, detail="Start date cannot be later than yesterday"
#         )

#     try:
#         result_summary = await run_data_generation(
#             fdq.start_date,
#             fdq.end_date,
#             fdq.max_fake_users_per_day,
#             fdq.max_user_churn,
#             fdq.max_first_shop_creation_percentage,
#             fdq.max_multiple_shop_creation_percentage,
#             fdq.max_shop_churn,
#         )
#     except Exception as e:
#         logger.error(f"Data generation failed: {str(e)}")
#         raise HTTPException(
#             status_code=500, detail=f"Data generation failed: {str(e)}"
#         )

#     logger.info(f"Fake data generation completed successfully for {fdq.start_date} to {fdq.end_date}")
    
#     return {
#         "message": "Fake data generation completed",
#         "start_date": fdq.start_date.isoformat(),
#         "end_date": fdq.end_date.isoformat(),
#         "summary": result_summary,
#     }