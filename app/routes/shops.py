from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from dateutil.parser import parse
import pytz
from .. import models, schemas, database

router = APIRouter()

@router.post("/create_shop/", response_model=schemas.GlobalEventResponse)
def create_shop(shop: schemas.ShopCreate, db: Session = Depends(database.get_db)):
    event_metadata = {
        "shop_id": str(uuid.uuid4()),
        "shop_owner_id": str(shop.shop_owner_id),
        "shop_name": shop.shop_name
    }

    new_event = models.GlobalEvent.create_with_partition(
        db,
        event_time=database.parse_event_time(shop.event_time),
        event_type=models.EventType.user_shop_create,
        event_metadata=event_metadata
    )

    return new_event.response

@router.post("/delete_shop/", response_model=schemas.GlobalEventResponse)
def delete_shop(shop: schemas.ShopDelete, db: Session = Depends(database.get_db)):
    event_metadata = {
        "shop_id": str(shop.shop_id),
        "shop_owner_id": str(shop.shop_owner_id) if shop.shop_owner_id else None
    }

    new_event = models.GlobalEvent.create_with_partition(
        db,
        event_time=database.parse_event_time(shop.event_time),
        event_type=models.EventType.user_shop_delete,
        event_metadata=event_metadata
    )

    return new_event.response