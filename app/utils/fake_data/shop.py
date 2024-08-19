from datetime import datetime
import uuid
from typing import  Optional
from pydantic import BaseModel


from .new_fake_data_generator_helpers import (
    api_request,
    generate_event_time,
    BASE_URL,
    logger,
)

class Shop(BaseModel):
    id: uuid.UUID
    shop_owner_id: uuid.UUID
    shop_name: str
    created_time: datetime
    deactivated_time: Optional[datetime] = None



    async def deactivate(self,current_date, event_time= None,   client=None):
        if not event_time:
            event_time = generate_event_time(current_date)
        if event_time > self.created_time and not self.deactivated_time:
            self.deactivated_time = event_time
            payload = {"shop_id": self.id, "event_time": self.deactivated_time}
            response = await api_request(
                client, "POST", f"{BASE_URL}/delete_shop/", payload
            )
            if response:
                return self
            else:
                logger.error(
                    f"Shop deletion failed for email: {self.shop_name}"
                )

                
            self.deactivated_time = event_time
            return self
        return None