from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime
from typing import Dict, Union, Optional
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


class ShopCreate(BaseModel):
    user_id: str
    shop_name: str

    class Config:
        orm_mode = True


class ShopDelete(BaseModel):
    shop_id: str
    user_id: Optional[str] = None  # Optional, depending on your business logic

    class Config:
        orm_mode = True
