from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional
import pytz

class FakeDataQuery(BaseModel):
    start_date: datetime = Field(default_factory=lambda: (datetime.now(pytz.utc) - timedelta(days=14)).replace(hour=0, minute=0, second=0, microsecond=0))
    end_date: datetime = Field(default_factory=lambda: (datetime.now(pytz.utc) - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999))
    max_fake_users_per_day: Optional[int] = 1000
    max_user_churn: Optional[float] = 0.1
    max_first_shop_creation_percentage: Optional[float] = 0.9
    max_multiple_shop_creation_percentage: Optional[float] = 0.2
    max_shop_churn: Optional[float] = 0.2

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "start_date": "2024-08-10T01:27:57.369Z",
                "end_date": "2024-08-16T01:27:57.369Z",
                "max_fake_users_per_day": 1000,
                "max_user_churn": 0.1,
                "max_first_shop_creation_percentage": 0.8,
                "max_multiple_shop_creation_percentage": 0.1,
                "max_shop_churn": 0.2
            }
        }