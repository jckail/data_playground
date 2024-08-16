from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, String, text
from datetime import datetime, timedelta
from fastapi import  HTTPException
from sqlalchemy.orm import  declarative_mixin

Base = declarative_base()

def generate_partition_name(tablename, partition_key):
    return f"{tablename}_p_{partition_key.replace('-', '_').replace(':', '_')}"


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
            partition_key = event_time.strftime("%Y-%m-%dT%H:00:00")
            #next_partition = (event_time + timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00")
            partition_name = generate_partition_name(self.__tablename__, partition_key.replace(':', '_'))
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {self.__tablename__}
                FOR VALUES IN ('{partition_key}')
            """))
        elif self.__partitiontype__ == "daily":
            partition_key = event_time.strftime("%Y-%m-%d")
            next_partition = (event_time + timedelta(days=1)).strftime("%Y-%m-%d")
            partition_name = generate_partition_name(self.__tablename__, partition_key.replace(':', '_'))
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {self.__tablename__}
                FOR VALUES FROM ('{partition_key}') TO ('{next_partition}')
            """))
        else:
            raise ValueError("Invalid partition type")


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
            raise HTTPException(status_code=500, detail=f"Failed to create {cls.__name__}: {str(e)}")


    @classmethod
    def validate_partition(cls, db,   **kwargs):
        try:
            instance = cls(**kwargs)
            instance.partition_key = instance.generate_partition_key(db)
            return instance
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to create {cls.__name__}: {str(e)}")
