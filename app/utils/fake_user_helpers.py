from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import User
from typing import Dict, Union

def create_fake_user_metadata(fake_user_id: str, email: str) -> Dict[str, str]:
    # This function doesn't interact with the database, so it doesn't need to be async
    return {
        "fake_user_id": fake_user_id,  # Updated from user_id
        "email": email
    }

async def get_fake_user_by_identifier(db: AsyncSession, identifier: str) -> Union[User, None]:
    if '@' in identifier:
        stmt = select(User).where(User.email == identifier)
    else:
        stmt = select(User).where(User.id == identifier)
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
