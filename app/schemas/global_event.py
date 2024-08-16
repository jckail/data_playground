# app/schemas/global_event.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict
import uuid

class GlobalEventResponse(BaseModel):
    event_id: str = Field(..., description="UUID of the event")
    event_time: datetime
    event_type: str
    event_metadata: Dict

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Convert UUID to string if necessary
        if isinstance(obj.event_id, uuid.UUID):
            obj.event_id = str(obj.event_id)
        return super().from_orm(obj)

class GlobalEventCreate(BaseModel):
    event_type: str
    event_metadata: Dict

    class Config:
        from_attributes = True

