from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import GlobalEvent, EventType
from ..schemas import FakeUserCreate, FakeUserDeactivate, GlobalEventResponse
from ..database import get_db, parse_event_time
from ..utils.fake_user_helpers import create_fake_user_metadata, get_fake_user_by_identifier
import uuid
import logging

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

@router.post("/create_fake_user/", response_model=GlobalEventResponse)
async def create_fake_user(fake_user: FakeUserCreate, db: AsyncSession = Depends(get_db)):
    try:
        event_metadata = create_fake_user_metadata(str(uuid.uuid4()), fake_user.email)

        new_event = await GlobalEvent.create_with_partition(
            db,
            event_time=await parse_event_time(fake_user.event_time),
            event_type=EventType.fake_user_account_creation,  # Updated event type
            event_metadata=event_metadata
        )

        return GlobalEventResponse.from_orm(new_event)

    except Exception as e:
        logger.error(f"Failed to create fake user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create fake user")


@router.post("/deactivate_fake_user/", response_model=GlobalEventResponse)
async def deactivate_fake_user(fake_user: FakeUserDeactivate, db: AsyncSession = Depends(get_db)):
    try:
        # Determine if the identifier is an email or fake_user_id and create event metadata accordingly
        if '@' in fake_user.identifier:
            event_metadata = {
                "email": fake_user.identifier
            }
        else:
            event_metadata = {
                "fake_user_id": fake_user.identifier  # Updated from user_id
            }

        new_event = await GlobalEvent.create_with_partition(
            db,
            event_time=await parse_event_time(fake_user.event_time),
            event_type=EventType.fake_user_deactivate_account,  # Updated event type
            event_metadata=event_metadata
        )

        return GlobalEventResponse.from_orm(new_event)

    except Exception as e:
        logger.error(f"Failed to deactivate fake user: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate fake user")

# Commented out legacy code preserved for reference
# @router.post("/deactivate_fake_user/", response_model=GlobalEventResponse)
# def deactivate_fake_user(fake_user: FakeUserDeactivate, db: Session = Depends(get_db)):
#     db_user = get_fake_user_by_identifier(db, fake_user.identifier)
#     if not db_user:
#         raise HTTPException(status_code=404, detail="Fake user not found")
#
#     event_metadata = create_fake_user_metadata(str(db_user.id), db_user.email)
#
#     new_event = GlobalEvent.create_with_partition(
#         db,
#         event_time=parse_event_time(fake_user.event_time),
#         event_type=EventType.fake_user_deactivate_account,
#         event_metadata=event_metadata
#     )
#
#     return GlobalEventResponse.from_orm(new_event)

# @router.get("/fake_user/{fake_user_id}", response_model=GlobalEventResponse)
# def get_fake_user(fake_user_id: uuid.UUID, db: Session = Depends(get_db)):
#     db_user = get_fake_user_by_identifier(db, str(fake_user_id))
#     if not db_user:
#         raise HTTPException(status_code=404, detail="Fake user not found")
#
#     event_metadata = create_fake_user_metadata(str(db_user.id), db_user.email)
#
#     return GlobalEventResponse(
#         event_id=str(uuid.uuid4()),
#         event_time=db_user.created_time,
#         event_type=EventType.fake_user_account_creation.value,
#         event_metadata=event_metadata
#     )
