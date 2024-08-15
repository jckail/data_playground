from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from .. import models, schemas, database
from datetime import datetime, timedelta
from typing import List
import uuid

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/events/", response_model=schemas.GlobalEventResponse)
def create_event(event: schemas.GlobalEventCreate, db: Session = Depends(get_db)):
    event_time = datetime.utcnow()
    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=event.event_type,
        event_metadata=event.event_metadata,
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

@router.get("/events/{event_id}", response_model=schemas.GlobalEventResponse)
def read_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    event = db.query(models.GlobalEvent).filter(models.GlobalEvent.event_id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return schemas.GlobalEventResponse(
        event_id=event.event_id,
        event_time=event.event_time,
        event_type=event.event_type,
        event_metadata=event.event_metadata
    )

@router.get("/events/", response_model=List[schemas.GlobalEventResponse])
def read_events(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    events = db.query(models.GlobalEvent).offset(skip).limit(limit).all()
    return [schemas.GlobalEventResponse(
        event_id=event.event_id,
        event_time=event.event_time,
        event_type=event.event_type,
        event_metadata=event.event_metadata
    ) for event in events]

# Add a function to create partitions for the next 24 hours
def create_partitions(db: Session):
    start_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    for i in range(24):
        partition_time = start_time + timedelta(hours=i)
        partition_key = models.GlobalEvent.generate_partition_key(partition_time)
        partition_name = f"global_events_{partition_key.replace('-', '_').replace(':', '_')}"
        db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF global_events
        FOR VALUES IN ('{partition_key}')
        """))
    db.commit()

# Call this function when your app starts
def startup_event():
    db = next(get_db())
    create_partitions(db)
    db.close()