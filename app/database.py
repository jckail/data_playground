from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import logging
from sqlalchemy.exc import InterfaceError
from sqlalchemy import text
from datetime import datetime
import pytz
from dateutil.parser import parse
from fastapi import HTTPException

import asyncio

logger = logging.getLogger("streamlit_app")
logging.basicConfig(level=logging.INFO)


SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@db/dbname"
)
# Get connection pool settings from environment variables
POOL_SIZE = int(os.getenv("POOL_SIZE", 20))
MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", 10))
POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", 30))
POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", 1800))

# Create the engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
)

# Create sessionmaker
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db():
    """Coroutine that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

logger.info("Database connection setup completed.")

semaphore = asyncio.Semaphore(25)

async def execute_query(query: str, retries=3):
    """Execute a SQL query with retries on interface errors."""
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
                logger.warning(f"Interface error on attempt {attempt + 1}, retrying...")
                await asyncio.sleep(1)  # Wait a bit before retrying
            else:
                logger.error("Failed to execute query after multiple attempts.")
                raise e

async def parse_event_time(event_time):
    """Parse and return a datetime object from various input formats."""
    try:
        if isinstance(event_time, str):
            event_time = parse(event_time)
        elif event_time is None:
            event_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif not isinstance(event_time, datetime):
            raise ValueError("event_time must be a datetime object or a valid datetime string")

        return event_time
    except Exception as e:
        logger.error(f"Invalid datetime format for event_time: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")
