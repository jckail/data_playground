from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database
from datetime import datetime
from dateutil.parser import parse
import uuid
import pytz

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/invoice_payment/", response_model=schemas.GlobalEventResponse)
def invoice_payment(payment: schemas.PaymentCreate, db: Session = Depends(get_db)):
    payment_id = str(uuid.uuid4())

    try:
        # Parse and validate event_time
        if isinstance(payment.event_time, str):
            event_time = parse(payment.event_time)
        elif payment.event_time is None:
            event_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif isinstance(payment.event_time, datetime):
            event_time = payment.event_time
        else:
            raise ValueError("event_time must be a datetime object or a valid datetime string")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")

    # Check if the invoice exists
    invoice = db.query(models.UserInvoice).filter(models.UserInvoice.invoice_id == payment.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Create the payment record
    new_payment = models.Payment(
        payment_id=payment_id,
        invoice_id=payment.invoice_id,
        payment_amount=payment.payment_amount,
        event_time=event_time,
        partition_key=event_time.date()  # Assuming partition_key is based on the date
    )
    db.add(new_payment)
    
    # Partition name
    partition_name = f"payments_{event_time.date().strftime('%Y_%m_%d')}"
    database.create_partition_if_not_exists(db, partition_name, event_time.date())
    
    db.commit()
    db.refresh(new_payment)
    
    # Prepare the response
    event_metadata = {
        "payment_id": payment_id,
        "invoice_id": payment.invoice_id,
        "payment_amount": payment.payment_amount
    }

    new_event = models.GlobalEvent(
        event_time=event_time,
        event_type=models.EventType.user_shop_create,  # Assuming you have an event type for payments
        event_metadata=event_metadata,
        partition_key=models.GlobalEvent.generate_partition_key(event_time)
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return schemas.GlobalEventResponse(
        event_id=new_event.event_id,
        event_time=new_event.event_time,
        event_type=new_event.event_type,
        event_metadata=new_event.event_metadata
    )
