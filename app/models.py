from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base
import uuid
import enum

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class EventType(enum.Enum):
    USER_REGISTERED = "user_registered"
    USER_LOGGED_IN = "user_logged_in"
    PURCHASE_MADE = "purchase_made"
    ITEM_ADDED_TO_CART = "item_added_to_cart"
    ITEM_REMOVED_FROM_CART = "item_removed_from_cart"

class GlobalEvent(Base):
    __tablename__ = "global_events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    event_metadata = Column(JSON, nullable=True)