from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError
from .. import models, schemas, database
from datetime import datetime
import uuid

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/create_user/", response_model=schemas.GlobalEventResponse)
def create_user(user: schemas.UserCreate, event_time: datetime = None, db: Session = Depends(get_db)):
    user_id = str(uuid.uuid4())
    if event_time is None:
        event_time = datetime.utcnow()
    event_metadata = {
        "user_id": user_id,
        "email": user.email
    }
    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=models.EventType.user_account_creation,
        event_metadata=event_metadata,
        partition_key=models.GlobalEvent.generate_partition_key(event_time)
    )
    db.add(new_event)
    
    # Create partition if it doesn't exist
    partition_name = f"global_events_{new_event.partition_key.replace('-', '_').replace(':', '_')}"
    try:
        db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF global_events
        FOR VALUES IN ('{new_event.partition_key}')
        """))
        db.commit()  # Commit the transaction if the table creation is successful
    except ProgrammingError as e:
        db.rollback()  # Rollback if an error occurs to maintain database integrity
        if "DuplicateTable" not in str(e.orig):
            raise e  # Re-raise if the error is not a DuplicateTable error
    
    db.refresh(new_event)
    
    return schemas.GlobalEventResponse(
        event_id=new_event.event_id,
        event_time=new_event.event_time,
        event_type=new_event.event_type,
        event_metadata=new_event.event_metadata
    )

@router.post("/deactivate_user/", response_model=schemas.GlobalEventResponse)
def deactivate_user(user: schemas.UserDeactivate, event_time: datetime = None, db: Session = Depends(get_db)):
    if event_time is None:
        event_time = datetime.utcnow()
    
    # Determine if the identifier is an email or user_id
    if '@' in user.identifier:
        event_metadata = {
            "email": user.identifier
        }
    else:
        event_metadata = {
            "user_id": user.identifier
        }

    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=models.EventType.user_deactivate_account,
        event_metadata=event_metadata,
        partition_key=models.GlobalEvent.generate_partition_key(event_time)
    )
    db.add(new_event)
    
    # Create partition if it doesn't exist
    partition_name = f"global_events_{new_event.partition_key.replace('-', '_').replace(':', '_')}"
    db.execute(text(f"""
    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF global_events
    FOR VALUES IN ('{new_event.partition_key}')
    """))
    
    db.commit()
    db.refresh(new_event)
    
    return schemas.GlobalEventResponse(
        event_id=new_event.event_id,
        event_time=new_event.event_time,
        event_type=new_event.event_type,
        event_metadata=new_event.event_metadata
    )