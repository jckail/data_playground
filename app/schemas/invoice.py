# app/schemas/invoice.py

from pydantic import BaseModel, UUID4, Field
from datetime import datetime

class FakeUserInvoiceCreate(BaseModel):
    fake_user_id: UUID4  # Updated from user_id
    shop_id: UUID4
    invoice_amount: float
    event_time: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

class FakeUserInvoice(BaseModel):  # Updated from UserInvoice
    invoice_id: UUID4
    fake_user_id: UUID4  # Updated from user_id
    shop_id: UUID4
    invoice_amount: float
    event_time: datetime

    class Config:
        from_attributes = True
