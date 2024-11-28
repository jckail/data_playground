from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, String, text, DDL, event, MetaData
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.exc import SQLAlchemyError

# Create a naming convention for constraints and indexes
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Create metadata with naming convention and schema
metadata = MetaData(
    naming_convention=NAMING_CONVENTION,
    schema="data_playground"
)

class Base(AsyncAttrs, DeclarativeBase):
    metadata = metadata

    # Set schema for all models
    @declared_attr.directive
    def __table_args__(cls):
        return {'schema': 'data_playground'}

def generate_partition_name(tablename, partition_key):
    return f"{tablename}_p_{partition_key.replace('-', '_').replace(':', '_')}".lower()

@declarative_mixin
class PartitionedModel:
    # Include partition_key in primary key
    partition_key = Column(String, nullable=False, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @declared_attr
    def __table_args__(cls):
        # Default table args for partitioned tables
        return {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }

    async def generate_partition_key(self, db):
        event_time = getattr(self, self.__partition_field__, None)
        if not isinstance(event_time, datetime):
            print(f"Invalid Datetime {self.__partition_field__} type: {event_time} --> {type(event_time)}")
            event_time = datetime.utcnow()

        partition_name = ""
        partition_key = ""

        try:
            if self.__partitiontype__ == "hourly":
                partition_key = event_time.strftime("%Y-%m-%dT%H:00:00")
                partition_name = generate_partition_name(self.__tablename__, partition_key.replace(':', '_')).lower()
                print(f"Checking partition {partition_name} for {self.__tablename__} with partition key {partition_key}")
                
                await db.execute(text(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT FROM pg_tables
                            WHERE schemaname = 'data_playground' AND tablename = '{partition_name}'
                        ) THEN
                            CREATE TABLE IF NOT EXISTS data_playground.{partition_name} PARTITION OF data_playground.{self.__tablename__}
                            FOR VALUES FROM ('{partition_key}') TO ('{(event_time + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")}');
                        ELSE
                            RAISE NOTICE 'Partition {partition_name} already exists';
                        END IF;
                    END $$;
                """))
            elif self.__partitiontype__ == "daily":
                partition_key = event_time.strftime("%Y-%m-%d")
                next_partition = (event_time + timedelta(days=1)).strftime("%Y-%m-%d")
                partition_name = generate_partition_name(self.__tablename__, partition_key.replace(':', '_')).lower()
                await db.execute(text(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT FROM pg_tables
                            WHERE schemaname = 'data_playground' AND tablename = '{partition_name}'
                        ) THEN
                            CREATE TABLE IF NOT EXISTS data_playground.{partition_name} PARTITION OF data_playground.{self.__tablename__}
                            FOR VALUES FROM ('{partition_key}') TO ('{next_partition}');
                        ELSE
                            RAISE NOTICE 'Partition {partition_name} already exists';
                        END IF;
                    END $$;
                """))
            else:
                raise ValueError("Invalid partition type")

            await db.commit()
            
        except SQLAlchemyError as e:
            await db.rollback()
            print(f"Error while creating partition for {self.__tablename__}: {str(e)}")

        return partition_key

    @classmethod
    async def create_with_partition(cls, db, **kwargs):
        try:
            instance = cls(**kwargs)
            instance.partition_key = await instance.generate_partition_key(db)
            db.add(instance)
            await db.commit()
            await db.refresh(instance)
            return instance
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create {cls.__name__}: {str(e)}")

    @classmethod
    async def validate_partition(cls, db, **kwargs):
        try:
            instance = cls(**kwargs)
            instance.partition_key = await instance.generate_partition_key(db)
            return instance
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create {cls.__name__}: {str(e)}")

# Event listener to ensure schema exists and is set as default
@event.listens_for(Base.metadata, 'before_create')
def create_schema(target, connection, **kw):
    # Create schema if it doesn't exist
    connection.execute(DDL('CREATE SCHEMA IF NOT EXISTS data_playground'))
    # Set search_path to ensure types are created in data_playground schema
    connection.execute(DDL('SET search_path TO data_playground'))

# Event listener to ensure types are created in data_playground schema
@event.listens_for(Base.metadata, 'after_create')
def set_default_schema(target, connection, **kw):
    # Reset search_path after creating tables
    connection.execute(DDL('SET search_path TO public'))
