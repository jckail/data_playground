from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from dateutil.parser import parse
import pytz
from .. import models, schemas, database

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create_shop/", response_model=schemas.GlobalEventResponse)
def create_shop(shop: schemas.ShopCreate, db: Session = Depends(get_db)):
    shop_id = uuid.uuid4()  # Keep as UUID for proper storage and conversion

    try:
        # Parse and validate event_time
        if isinstance(shop.event_time, str):
            event_time = parse(shop.event_time)
        elif shop.event_time is None:
            event_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif isinstance(shop.event_time, datetime):
            event_time = shop.event_time
        else:
            raise ValueError("event_time must be a datetime object or a valid datetime string")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")

    event_metadata = {
        "shop_id": str(shop_id),  # Convert UUID to string for metadata storage
        "user_id": str(shop.user_id),  # Convert UUID to string for metadata storage
        "shop_name": shop.shop_name
    }

    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=models.EventType.user_shop_create,
        event_metadata=event_metadata,
        partition_key=models.GlobalEvent.generate_partition_key(event_time)
    )
    db.add(new_event)
    
    try:
        database.create_partition_if_not_exists(db, "global_events", new_event.partition_key)
        
        db.commit()
        db.refresh(new_event)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create shop: {e}")
    
    return schemas.GlobalEventResponse(
        event_id=str(new_event.event_id),  # Convert UUID to string for response
        event_time=new_event.event_time,
        event_type=new_event.event_type.value,  # Convert Enum to string for response
        event_metadata=new_event.event_metadata
    )

@router.post("/delete_shop/", response_model=schemas.GlobalEventResponse)
def delete_shop(shop: schemas.ShopDelete, db: Session = Depends(get_db)):
    try:
        # Parse and validate event_time
        if isinstance(shop.event_time, str):
            event_time = parse(shop.event_time)
        elif shop.event_time is None:
            event_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif isinstance(shop.event_time, datetime):
            event_time = shop.event_time
        else:
            raise ValueError("event_time must be a datetime object or a valid datetime string")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")

    event_metadata = {
        "shop_id": str(shop.shop_id),  # Convert UUID to string for metadata storage
        "user_id": str(shop.user_id) if shop.user_id else None  # Convert UUID to string if user_id is provided
    }

    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=models.EventType.user_shop_delete,
        event_metadata=event_metadata,
        partition_key=models.GlobalEvent.generate_partition_key(event_time)
    )
    db.add(new_event)
    
    try:
        # Partition name
        partition_name = f"global_events_{new_event.partition_key.replace('-', '_').replace(':', '_')}"
        
        # Call the utility function to check and create the partition
        database.create_partition_if_not_exists(db, partition_name, new_event.partition_key)
        
        db.commit()
        db.refresh(new_event)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete shop: {e}")
    
    return schemas.GlobalEventResponse(
        event_id=str(new_event.event_id),  # Convert UUID to string for response
        event_time=new_event.event_time,
        event_type=new_event.event_type.value,  # Convert Enum to string for response
        event_metadata=new_event.event_metadata
    )
