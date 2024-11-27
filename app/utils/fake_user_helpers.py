from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import FakeUser
from typing import Dict, Union

def create_fake_user_metadata(fake_user_id: str, email: str) -> Dict[str, str]:
    # This function doesn't interact with the database, so it doesn't need to be async
    return {
        "fake_user_id": fake_user_id,  # Updated from user_id
        "email": email
    }

async def get_fake_user_by_identifier(db: AsyncSession, identifier: str) -> Union[FakeUser, None]:
    if '@' in identifier:
        stmt = select(FakeUser).where(FakeUser.email == identifier)
    else:
        stmt = select(FakeUser).where(FakeUser.id == identifier)
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
