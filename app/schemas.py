from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime
from typing import Dict, Union
from . import models

class UserCreate(BaseModel):
    email: EmailStr

class UserDeactivate(BaseModel):
    identifier: Union[EmailStr, str]

class GlobalEventCreate(BaseModel):
    event_type: models.EventType
    event_metadata: Dict

class GlobalEventResponse(BaseModel):
    event_id: UUID4
    event_time: datetime
    event_type: models.EventType
    event_metadata: Dict