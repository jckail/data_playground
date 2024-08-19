from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import GlobalEvent, EventType
from ..schemas import UserCreate, UserDeactivate, GlobalEventResponse
from ..database import get_db, parse_event_time
from ..utils.user_helpers import create_user_metadata, get_user_by_identifier
import uuid
import logging

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

@router.post("/create_user/", response_model=GlobalEventResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        event_metadata = create_user_metadata(str(uuid.uuid4()), user.email)

        new_event = await GlobalEvent.create_with_partition(
            db,
            event_time=await parse_event_time(user.event_time),
            event_type=EventType.user_account_creation,
            event_metadata=event_metadata
        )

        return GlobalEventResponse.from_orm(new_event)

    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.post("/deactivate_user/", response_model=GlobalEventResponse)
async def deactivate_user(user: UserDeactivate, db: AsyncSession = Depends(get_db)):
    try:
        # Determine if the identifier is an email or user_id and create event metadata accordingly
        if '@' in user.identifier:
            event_metadata = {
                "email": user.identifier
            }
        else:
            event_metadata = {
                "user_id": user.identifier
            }

        new_event = await GlobalEvent.create_with_partition(
            db,
            event_time=await parse_event_time(user.event_time),
            event_type=EventType.user_deactivate_account,
            event_metadata=event_metadata
        )

        return GlobalEventResponse.from_orm(new_event)

    except Exception as e:
        logger.error(f"Failed to deactivate user: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate user")


# @router.post("/deactivate_user/", response_model=GlobalEventResponse)
# def deactivate_user(user: UserDeactivate, db: Session = Depends(get_db)):
#     db_user = get_user_by_identifier(db, user.identifier)
#     if not db_user:
#         raise HTTPException(status_code=404, detail="User not found")

#     event_metadata = create_user_metadata(str(db_user.id), db_user.email)

#     new_event = GlobalEvent.create_with_partition(
#         db,
#         event_time=parse_event_time(user.event_time),
#         event_type=EventType.user_deactivate_account,
#         event_metadata=event_metadata
#     )

#     # Here you might want to actually deactivate the user in the database
#     # db_user.is_active = False
#     # db.commit()

#     return GlobalEventResponse.from_orm(new_event)

# @router.get("/user/{user_id}", response_model=GlobalEventResponse)
# def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
#     db_user = get_user_by_identifier(db, str(user_id))
#     if not db_user:
#         raise HTTPException(status_code=404, detail="User not found")

#     event_metadata = create_user_metadata(str(db_user.id), db_user.email)

#     return GlobalEventResponse(
#         event_id=str(uuid.uuid4()),
#         event_time=db_user.created_time,
#         event_type=EventType.user_account_creation.value,
#         event_metadata=event_metadata
#     )