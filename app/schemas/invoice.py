# app/schemas/invoice.py

from pydantic import BaseModel, UUID4, Field
from datetime import datetime

class InvoiceCreate(BaseModel):
    user_id: UUID4
    shop_id: UUID4
    invoice_amount: float
    event_time: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

class UserInvoice(BaseModel):
    invoice_id: UUID4
    user_id: UUID4
    shop_id: UUID4
    invoice_amount: float
    event_time: datetime

    class Config:
        from_attributes = True