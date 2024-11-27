# app/schemas/fake_user.py

from pydantic import BaseModel, validator, EmailStr, UUID4
from datetime import datetime
from typing import Optional
from typing import Dict
import uuid

class FakeUserCreate(BaseModel):
    email: EmailStr
    event_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class FakeUserDeactivate(BaseModel):
    identifier: str
    event_time: Optional[datetime] = None

    @validator('identifier')
    def validate_identifier(cls, v):
        if '@' in v:
            # It's an email
            return v
        try:
            # Try to parse it as UUID
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("identifier must be either a valid email address or a valid UUID")

    class Config:
        from_attributes = True

class FakeUserResponse(BaseModel):
    fake_user_id: UUID4  # Updated from user_id
    email: EmailStr
    event_time: datetime

    class Config:
        from_attributes = True

class FakeUserSnapshot(BaseModel):
    event_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class FakeUserSnapshotResponse(BaseModel):
    event_time: datetime
    event_type: str
    event_metadata: Dict

    class Config:
        from_attributes = True
