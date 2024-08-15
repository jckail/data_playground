from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, database
from .database import engine
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, Dict, List
import uuid

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

class ItemCreate(BaseModel):
    name: str

class GlobalEventCreate(BaseModel):
    event_time: datetime
    event_type: models.EventType
    event_metadata: Optional[Dict] = None

class GlobalEventResponse(BaseModel):
    event_id: UUID4
    event_time: datetime
    event_type: models.EventType
    event_metadata: Optional[Dict] = None

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Item endpoints (unchanged)
@app.post("/items/", response_model=dict)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    new_item = models.Item(name=item.name)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"id": new_item.id, "name": new_item.name}

@app.get("/items/{item_id}", response_model=dict)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item.id, "name": item.name}

@app.get("/items/", response_model=List[dict])
def read_items(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    items = db.query(models.Item).offset(skip).limit(limit).all()
    return [{"id": item.id, "name": item.name} for item in items]

# Global Event endpoints
@app.post("/events/", response_model=GlobalEventResponse)
def create_event(event: GlobalEventCreate, db: Session = Depends(get_db)):
    new_event = models.GlobalEvent(
        event_time=event.event_time,
        event_type=event.event_type,
        event_metadata=event.event_metadata
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return GlobalEventResponse(
        event_id=new_event.event_id,
        event_time=new_event.event_time,
        event_type=new_event.event_type,
        event_metadata=new_event.event_metadata
    )

@app.get("/events/{event_id}", response_model=GlobalEventResponse)
def read_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    event = db.query(models.GlobalEvent).filter(models.GlobalEvent.event_id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return GlobalEventResponse(
        event_id=event.event_id,
        event_time=event.event_time,
        event_type=event.event_type,
        event_metadata=event.event_metadata
    )

@app.get("/events/", response_model=List[GlobalEventResponse])
def read_events(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    events = db.query(models.GlobalEvent).offset(skip).limit(limit).all()
    return [GlobalEventResponse(
        event_id=event.event_id,
        event_time=event.event_time,
        event_type=event.event_type,
        event_metadata=event.event_metadata
    ) for event in events]