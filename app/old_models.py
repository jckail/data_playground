from sqlalchemy import Column, DateTime,  Enum, String,  Float , Boolean, ForeignKey, Date, ForeignKeyConstraint
from sqlalchemy.sql import text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import declarative_base, declarative_mixin
from sqlalchemy.ext.declarative import declared_attr
import uuid
import enum
from datetime import datetime
import asyncio
from . import  schemas
from fastapi import  HTTPException
from sqlalchemy.ext.hybrid import hybrid_property


Base = declarative_base()

class EventType(enum.Enum):
    user_account_creation = "user_account_creation"
    user_delete_account = "user_delete_account"
    user_shop_create = "user_shop_create"
    user_shop_delete = "user_shop_delete"
    user_deactivate_account = "user_deactivate_account"


#flow
# 


@declarative_mixin
class PartitionedModel:

    partition_key = Column(String, primary_key=True, nullable=False)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def generate_partition_key(self, db):
        event_time = getattr(self, self.__partition_field__, None)
        if not isinstance(event_time, datetime):
            print(f"Invalid Datetime {self.__partition_field__} type: {event_time} --> {type(event_time)}")
            event_time = datetime.utcnow()

        if self.__partitiontype__ == "hourly":
            partition_key = event_time.strftime("%Y-%m-%d:%H:00")
        elif self.__partitiontype__ == "daily":
            partition_key = event_time.strftime("%Y-%m-%d")
        else:
            raise ValueError("Invalid partition type")

        partition_name = f"{self.__tablename__}_p_{partition_key.replace('-', '_').replace(':', '_')}"
        db.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {self.__tablename__}
            FOR VALUES IN ('{partition_key}')
        """))
        db.commit()
        
        return partition_key

    @classmethod
    def create_with_partition(cls, db, **kwargs):
        try:
            instance = cls(**kwargs)
            instance.partition_key = instance.generate_partition_key(db)
            db.add(instance)
            db.commit()
            db.refresh(instance)
            return instance
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

class GlobalEvent(Base, PartitionedModel):
    __tablename__ = "global_events"
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_time = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    event_metadata = Column(JSON, nullable=True)
    
    __table_args__ = {'postgresql_partition_by': 'LIST (partition_key)'}

    @hybrid_property
    def response(self):
        return schemas.GlobalEventResponse(
            event_id=str(self.event_id),
            event_time=self.event_time,
            event_type=self.event_type.value,
            event_metadata=self.event_metadata
        )

class User(Base, PartitionedModel):
    __tablename__ = 'users'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False)
    status = Column(Boolean, nullable=False, default=True)
    created_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deactivated_time = Column(DateTime(timezone=True))
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())
    
    __table_args__ = {'postgresql_partition_by': 'RANGE (partition_key)'}



class Shop(Base, PartitionedModel):
    __tablename__ = 'shops'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_owner_id = Column(UUID(as_uuid=True), nullable=False)
    shop_name = Column(String(255), nullable=False)
    created_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    deactivated_time = Column(DateTime(timezone=True))
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())

    __table_args__ = (
        ForeignKeyConstraint(
            ['shop_owner_id', 'partition_key'],
            ['users.id', 'users.partition_key']
        ),
        {'postgresql_partition_by': 'RANGE (partition_key)'},
    )

class UserInvoice(Base, PartitionedModel):
    __tablename__ = 'user_invoices'

    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    shop_id = Column(UUID(as_uuid=True), nullable=False)
    invoice_amount = Column(Float, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())

    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id', 'partition_key'],
            ['users.id', 'users.partition_key']
        ),
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['shops.id', 'shops.partition_key']
        ),
        {'postgresql_partition_by': 'RANGE (partition_key)'},
    )

class Payment(Base, PartitionedModel):
    __tablename__ = 'payments'

    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), nullable=False)
    payment_amount = Column(Float, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    partition_key = Column(Date, primary_key=True, nullable=False, default=lambda: datetime.utcnow().date())

    __table_args__ = (
        ForeignKeyConstraint(
            ['invoice_id', 'partition_key'],
            ['user_invoices.invoice_id', 'user_invoices.partition_key']
        ),
        {'postgresql_partition_by': 'RANGE (partition_key)'},
    )


class EventPropensity:
    def __init__(
        self,
        max_fake_users_per_day=100,
        max_user_churn=0.1,
        max_first_shop_creation_percentage=0.8,
        max_multiple_shop_creation_percentage=0.1,
        max_shop_churn=0.2,
    ):
        self.max_fake_users_per_day = max_fake_users_per_day
        self.max_user_churn = max_user_churn
        self.max_first_shop_creation_percentage = max_first_shop_creation_percentage
        self.max_multiple_shop_creation_percentage = max_multiple_shop_creation_percentage
        self.max_shop_churn = max_shop_churn

class FakeHelper:
    def __init__(
        self,
        daily_users_created=0,
        daily_users_deactivated=0,
        daily_shops_created=0,
        daily_shops_deleted=0,
        semaphore=10,
        users=None,
        shops=None,
    ):
        self.daily_users_created = daily_users_created
        self.daily_users_deactivated = daily_users_deactivated
        self.daily_shops_created = daily_shops_created
        self.daily_shops_deleted = daily_shops_deleted

        self.users = users if users is not None else []
        self.shops = shops if shops is not None else []

        self.semaphore = asyncio.Semaphore(semaphore)
