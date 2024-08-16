from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

class ShopCreate(BaseModel):
    user_id: UUID4
    shop_name: str
    event_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class ShopResponse(BaseModel):
    shop_id: UUID4
    user_id: UUID4
    shop_name: str
    event_time: datetime

    class Config:
        from_attributes = True

class ShopDelete(BaseModel):
    shop_id: UUID4
    user_id: Optional[UUID4] = None
    event_time: Optional[datetime] = None

    class Config:
        from_attributes = True