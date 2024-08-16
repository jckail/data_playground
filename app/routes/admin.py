from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from ..utils.generate_fake_data import generate_fake_data
from datetime import datetime, timedelta, date
import pytz
from sqlalchemy import text
import httpx
from ..models import EventPropensity, FakeHelper, User, Shop
import time
from ..schemas import FakeDataQuery, UserSnapshot, UserSnapshotResponse, ShopSnapshot , ShopSnapshotResponse

from ..database import get_db

from app.utils.helpers import post_request, BASE_URL


router = APIRouter()


async def run_rollup(current_date, endpoint):
    event_time = current_date.isoformat()
    payload = {"event_time": current_date.isoformat()}
    url = f"{BASE_URL}/admin/{endpoint}"
    async with httpx.AsyncClient() as client:
        return await post_request(
            client,
            url,
            payload,
        f"Failed to run  {url} @ {event_time}",
    )

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
        await run_rollup(current_date, "user_snapshot")
        await run_rollup(current_date, "shop_snapshot")


    # Calculate the total runtime
    end_time = time.time()
    run_time = end_time - start_time

    #@TODO: FIX SUMMARY DICT the counts are wrong!
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
    fdq: FakeDataQuery,  # Use the schema defined in schemas.py
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    yesterday = datetime.now(pytz.utc).date() - timedelta(minutes=1)

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


@router.post("/user_snapshot", response_model=UserSnapshotResponse)
def user_snapshot(
    snapshot: UserSnapshot, db: Session = Depends(get_db)
):
    try:
        # Use the event_time from the schema, or default to current time
        event_time = snapshot.event_time or datetime.utcnow().replace(
            tzinfo=pytz.UTC
        )

        # Partition key based on the event_time
        partition_key = event_time.date()
        previous_day = partition_key - timedelta(days=1)

        print(f"partition_key: {partition_key}, type: {type(partition_key)}")
        print(f"previous_day: {previous_day}, type: {type(previous_day)}")

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


        res = db.execute(text(query))

        rows = res.fetchall()
        print(f"Fetched {len(rows)} rows")

        for i, row in enumerate(rows):
            # Check if the record already exists
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
                # Update existing record
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
                # Create new record
                db.add(new_record)

        db.commit()

        # Return the response after processing
        users_processed = get_users_processed_count(db, partition_key)
        
        return UserSnapshotResponse(
            event_time=event_time,
            event_type="user_snapshot",
            event_metadata={"users_processed": users_processed},
        )
        


    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"User snapshot failed: {e}"
        )





def get_users_processed_count(db: Session, partition_key: date) -> int:
    result = db.execute(
        text(f"SELECT COUNT(*) FROM users WHERE partition_key::date = '{partition_key}'::date"),
        {"partition_key": partition_key},
    ).scalar()
    return result


@router.post("/shop_snapshot", response_model=ShopSnapshotResponse)
def shop_snapshot(
    snapshot: ShopSnapshot, db: Session = Depends(get_db)
):
    try:
        # Use the event_time from the schema, or default to current time
        event_time = snapshot.event_time or datetime.utcnow().replace(
            tzinfo=pytz.UTC
        )

        # Partition key based on the event_time
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
        
        res = db.execute(text(query))

        rows = res.fetchall()
        print(f"Fetched {len(rows)} rows")

        for row in rows:
            # Check if the record already exists
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
                # Update existing record
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
                # Create new record
                db.add(new_record)

        db.commit()

        # Return the response after processing
        shops_processed = get_shops_processed_count(db, partition_key)
        
        return ShopSnapshotResponse(
            event_time=event_time,
            event_type="shop_snapshot",
            event_metadata={"shops_processed": shops_processed},
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Shop snapshot failed: {e}"
        )

def get_shops_processed_count(db: Session, partition_key: date) -> int:
    result = db.execute(
        text(f"SELECT COUNT(*) FROM shops WHERE partition_key::date = '{partition_key}'::date"),
        {"partition_key": partition_key},
    ).scalar()
    return result