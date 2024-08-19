from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError , InterfaceError
from sqlalchemy import text
import os
from datetime import timedelta, datetime
import pytz
from dateutil.parser import parse
from fastapi import HTTPException
import logging
import asyncio
logger = logging.getLogger("request_response_logger")
logging.basicConfig(level=logging.INFO)


SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@db/dbname"
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,    
    pool_size=250,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

semaphore = asyncio.Semaphore(10)



async def execute_query(query: str, retries=3):
    for attempt in range(retries):
        try:
            async with semaphore:
                async with AsyncSessionLocal() as session:
                    async with session.begin():  # Start a transaction
                        result = await session.execute(text(query))
                        rows = result.fetchall()
                        return [dict(row._mapping) for row in rows]
        except InterfaceError as e:
            if attempt < retries - 1:
                await asyncio.sleep(1)  # Wait a bit before retrying
                continue
            else:
                raise e
    
async def parse_event_time(event_time):
    """
    Parses and validates the event_time.
    
    Args:
        event_time: The event time, which can be a string, a datetime object, or None.
    
    Returns:
        A datetime object representing the parsed event time.
    
    Raises:
        HTTPException: If the event_time is not a valid datetime object or string.
    """
    try:
        if isinstance(event_time, str):
            event_time = parse(event_time)
        elif event_time is None:
            event_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif isinstance(event_time, datetime):
            pass
        else:
            raise ValueError("event_time must be a datetime object or a valid datetime string")
        
        return datetime.fromisoformat(event_time.isoformat())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")

