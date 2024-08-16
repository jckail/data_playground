from sqlalchemy.orm import Session
from ..models import User
from typing import Dict, Union

def create_user_metadata(user_id: str, email: str) -> Dict[str, str]:
    return {
        "user_id": user_id,
        "email": email
    }

def get_user_by_identifier(db: Session, identifier: str) -> Union[User, None]:
    if '@' in identifier:
        return db.query(User).filter(User.email == identifier).first()
    else:
        return db.query(User).filter(User.id == identifier).first()