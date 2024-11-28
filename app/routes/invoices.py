from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import models,  database
from datetime import datetime, timedelta
from ..schemas import FakeInvoice, FakeInvoiceCreate
from ..database import get_db, parse_event_time
import uuid

import logging
router = APIRouter()



logger = logging.getLogger(__name__)

@router.post("/create_FakeInvoice/", response_model=FakeInvoice)
def create_FakeInvoice_for_shops(FakeInvoice: FakeInvoiceCreate, db: Session = Depends(get_db)):
    try:
        new_FakeInvoice = models.FakeInvoice(
            FakeInvoice_id=uuid.uuid4(),
            user_id=FakeInvoice.user_id,
            shop_id=FakeInvoice.shop_id,
            FakeInvoice_amount=FakeInvoice.FakeInvoice_amount,
            event_time=FakeInvoice.event_time,
            partition_key=FakeInvoice.event_time.date()
        )

        db.add(new_FakeInvoice)
        db.commit()

        logger.info(f"FakeInvoice {new_FakeInvoice.FakeInvoice_id} created for shop {new_FakeInvoice.shop_id} and user {new_FakeInvoice.user_id}")

        return FakeInvoice.from_orm(new_FakeInvoice)

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create FakeInvoice: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create FakeInvoice: {e}")
