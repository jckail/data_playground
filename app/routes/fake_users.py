from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..models import GlobalEvent, EventType, User
from ..schemas import FakeUserCreate, FakeUserDeactivate, GlobalEventResponse, FakeUserResponse
from ..database import get_db, parse_event_time, engine
from ..utils.fake_user_helpers import create_fake_user_metadata, get_fake_user_by_identifier
from ..utils.partition_helper import check_and_create_partition
import uuid
import logging
from datetime import datetime
from faker import Faker
import random
import json

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Initialize Faker
fake = Faker()

@router.post("/create_fake_user/", response_model=FakeUserResponse)
async def create_fake_user(fake_user: FakeUserCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Create the User record
        event_time = await parse_event_time(fake_user.event_time) if fake_user.event_time else datetime.utcnow()
        
        new_user = User(
            username=fake_user.username,
            email=fake_user.email,
            phone_number=fake_user.phone_number,
            status=True,
            event_time=event_time,
            extra_data=fake_user.extra_data or {}
        )
        db.add(new_user)
        await db.flush()  # Get the ID without committing

        # Create the GlobalEvent for tracking
        event_metadata = create_fake_user_metadata(str(new_user.id), new_user.email)
        
        new_event = await GlobalEvent.create_with_partition(
            db,
            event_time=event_time,
            event_type=EventType.fake_user_account_creation,
            event_metadata=event_metadata,
            user_id=new_user.id  # Link the event to the user
        )

        await db.commit()
        return FakeUserResponse.from_orm(new_user)

    except Exception as e:
        if db is not None:
            await db.rollback()
        logger.error(f"Failed to create fake user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create fake user: {str(e)}")

@router.post("/deactivate_fake_user/", response_model=GlobalEventResponse)
async def deactivate_fake_user(fake_user: FakeUserDeactivate, db: AsyncSession = Depends(get_db)):
    try:
        # Find the user by email or ID
        if '@' in fake_user.identifier:
            user = await db.query(User).filter(User.email == fake_user.identifier).first()
        else:
            try:
                user_id = uuid.UUID(fake_user.identifier)
                user = await db.query(User).filter(User.id == user_id).first()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user ID format")

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user status and deactivation time
        event_time = await parse_event_time(fake_user.event_time) if fake_user.event_time else datetime.utcnow()
        user.status = False
        user.deactivated_time = event_time
        
        # Create deactivation event
        event_metadata = {
            "user_id": str(user.id),
            "email": user.email
        }

        new_event = await GlobalEvent.create_with_partition(
            db,
            event_time=event_time,
            event_type=EventType.fake_user_deactivate_account,
            event_metadata=event_metadata,
            user_id=user.id  # Link the event to the user
        )

        await db.commit()
        return GlobalEventResponse.from_orm(new_event)

    except Exception as e:
        if db is not None:
            await db.rollback()
        logger.error(f"Failed to deactivate fake user: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to deactivate fake user: {str(e)}")
