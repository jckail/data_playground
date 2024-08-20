from datetime import datetime
import uuid
from typing import  Optional
from pydantic import BaseModel


from ...routes.api_helpers import (
    api_request,
    generate_event_time,
    BASE_URL,
    logger,
)


#TODO: move this to actual app.models
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
            
            payload = {"shop_id": str(self.id), "event_time":event_time.isoformat()}
            response = await api_request(
                client, "POST", f"{BASE_URL}/delete_shop/", payload
            )
            if response:
                self.deactivated_time = event_time
                return self
            else:
                logger.error(
                    f"Shop deletion failed for shop: {self.shop_name}"
                )

                
            self.deactivated_time = event_time
            return self
        return None
    
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Shop):
            return self.id == other.id
        return False