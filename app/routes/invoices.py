from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import models,  database
from datetime import datetime, timedelta
from ..schemas import Invoice,InvoiceCreate
from ..database import get_db, parse_event_time
import uuid

import logging
router = APIRouter()



logger = logging.getLogger(__name__)

@router.post("/create_invoice/", response_model=Invoice)
def create_invoice_for_shops(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    try:
        new_invoice = models.Invoice(
            invoice_id=uuid.uuid4(),
            user_id=invoice.user_id,
            shop_id=invoice.shop_id,
            invoice_amount=invoice.invoice_amount,
            event_time=invoice.event_time,
            partition_key=invoice.event_time.date()
        )

        db.add(new_invoice)
        db.commit()

        logger.info(f"Invoice {new_invoice.invoice_id} created for shop {new_invoice.shop_id} and user {new_invoice.user_id}")

        return Invoice.from_orm(new_invoice)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create invoice: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {e}")
