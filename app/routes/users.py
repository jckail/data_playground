from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database
from datetime import datetime
import uuid
from dateutil.parser import parse
import pytz

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create_user/", response_model=schemas.GlobalEventResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user_id = uuid.uuid4()

    try:
        # Parse and validate event_time
        if isinstance(user.event_time, str):
            event_time = parse(user.event_time)
        elif user.event_time is None:
            event_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif isinstance(user.event_time, datetime):
            event_time = user.event_time
        else:
            raise ValueError("event_time must be a datetime object or a valid datetime string")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")
    
    # Create event metadata
    event_metadata = {
        "user_id": str(user_id),
        "email": user.email
    }

    # Create a new GlobalEvent
    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=models.EventType.user_account_creation,
        event_metadata=event_metadata,
        partition_key=models.GlobalEvent.generate_partition_key(event_time)
    )
    db.add(new_event)

    try:
        # Create the partition if it doesn't exist
        database.create_partition_if_not_exists(db, "global_events", new_event.partition_key)

        db.commit()
        db.refresh(new_event)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {e}")

    # Return the GlobalEvent response
    return schemas.GlobalEventResponse(
        event_id=str(new_event.event_id),
        event_time=new_event.event_time,
        event_type=new_event.event_type.value,
        event_metadata=new_event.event_metadata
    )


@router.post("/deactivate_user/", response_model=schemas.GlobalEventResponse)
def deactivate_user(user: schemas.UserDeactivate, db: Session = Depends(get_db)):
    try:
        # Parse and validate event_time
        if isinstance(user.event_time, str):
            event_time = parse(user.event_time)
        elif user.event_time is None:
            event_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif isinstance(user.event_time, datetime):
            event_time = user.event_time
        else:
            raise ValueError("event_time must be a datetime object or a valid datetime string")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")

    # Determine if the identifier is an email or user_id and create event metadata accordingly
    if '@' in user.identifier:
        event_metadata = {
            "email": user.identifier
        }
    else:
        event_metadata = {
            "user_id": user.identifier
        }

    # Create a new GlobalEvent for deactivation
    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=models.EventType.user_deactivate_account,
        event_metadata=event_metadata,
        partition_key=models.GlobalEvent.generate_partition_key(event_time)
    )
    db.add(new_event)
    
    try:
        # Define partition name
        partition_name = f"global_events_{new_event.partition_key.replace('-', '_').replace(':', '_')}"
        
        # Create the partition if it doesn't exist
        database.create_partition_if_not_exists(db, partition_name, new_event.partition_key)

        db.commit()
        db.refresh(new_event)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to deactivate user: {e}")

    # Return the GlobalEvent response
    return schemas.GlobalEventResponse(
        event_id=str(new_event.event_id),  # Convert UUID to string for response
        event_time=new_event.event_time,
        event_type=new_event.event_type.value,  # Convert EventType enum to string
        event_metadata=new_event.event_metadata
    )
