from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

class ShopCreate(BaseModel):
    shop_owner_id: UUID4
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
    shop_owner_id: Optional[UUID4] = None
    event_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class ShopSnapshot(BaseModel):
    event_time: Optional[datetime] = None

class ShopSnapshotResponse(BaseModel):
    event_time: datetime
    event_type: str
    event_metadata: dict