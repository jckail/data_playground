from pydantic import BaseModel, validator, EmailStr, UUID4, constr
from datetime import datetime
from typing import Optional, Dict
import uuid

class FakeUserCreate(BaseModel):
    username: constr(min_length=1, max_length=50)  # Match User model constraint
    email: EmailStr
    phone_number: Optional[str] = None
    event_time: Optional[datetime] = None
    extra_data: Optional[Dict] = None

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
    id: UUID4
    username: str
    email: EmailStr
    phone_number: Optional[str]
    status: bool
    created_time: datetime
    event_time: datetime
    extra_data: Optional[Dict]

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
