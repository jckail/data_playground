from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, String, text
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.exc import SQLAlchemyError

class Base(AsyncAttrs, DeclarativeBase):
    pass

def generate_partition_name(tablename, partition_key):
    return f"{tablename}_p_{partition_key.replace('-', '_').replace(':', '_')}".lower()

@declarative_mixin
class PartitionedModel:
    # Include partition_key in primary key
    partition_key = Column(String, nullable=False, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

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
