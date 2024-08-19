from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from dateutil.parser import parse
import pytz
import logging
from .. import models, schemas, database

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

@router.post("/create_shop/", response_model=schemas.GlobalEventResponse)
async def create_shop(shop: schemas.ShopCreate, db: Session = Depends(database.get_db)):
    try:
        event_metadata = {
            "shop_id": str(uuid.uuid4()),
            "shop_owner_id": str(shop.shop_owner_id),
            "shop_name": shop.shop_name
        }

        new_event = await models.GlobalEvent.create_with_partition(
            db,
            event_time=await database.parse_event_time(shop.event_time),
            event_type=models.EventType.user_shop_create,
            event_metadata=event_metadata
        )

        return schemas.GlobalEventResponse.from_orm(new_event)

    except Exception as e:
        logger.error(f"Failed to create shop: {e}")
        raise HTTPException(status_code=500, detail="Failed to create shop")

@router.post("/delete_shop/", response_model=schemas.GlobalEventResponse)
async def delete_shop(shop: schemas.ShopDelete, db: Session = Depends(database.get_db)):
    try:
        event_metadata = {
            "shop_id": str(shop.shop_id),
            "shop_owner_id": str(shop.shop_owner_id) if shop.shop_owner_id else None
        }

        new_event = await models.GlobalEvent.create_with_partition(
            db,
            event_time=await database.parse_event_time(shop.event_time),
            event_type=models.EventType.user_shop_delete,
            event_metadata=event_metadata
        )

        return schemas.GlobalEventResponse.from_orm(new_event)

    except Exception as e:
        logger.error(f"Failed to delete shop: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete shop")
