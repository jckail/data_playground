# app/schemas/payment.py

from pydantic import BaseModel, UUID4, Field
from datetime import datetime

class PaymentCreate(BaseModel):
    invoice_id: UUID4
    payment_amount: float
    event_time: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

class Payment(BaseModel):
    payment_id: UUID4
    invoice_id: UUID4
    payment_amount: float
    event_time: datetime

    class Config:
        from_attributes = True