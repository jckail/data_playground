from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError, InterfaceError
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

async def create_db_engine(max_retries=5, initial_wait=1):
    retries = 0
    wait = initial_wait
    while retries < max_retries:
        try:
            engine = create_async_engine(
                SQLALCHEMY_DATABASE_URL,    
                pool_size=250,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
            )
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return engine
        except OperationalError as e:
            if retries == max_retries - 1:
                logger.error(f"Failed to connect to the database after {max_retries} attempts")
                raise
            else:
                logger.warning(f"Database connection attempt {retries + 1} failed. Retrying in {wait} seconds...")
                await asyncio.sleep(wait)
                retries += 1
                wait *= 2

engine = None

async def get_engine():
    global engine
    if engine is None:
        engine = await create_db_engine()
    return engine

AsyncSessionLocal = None

async def get_async_session_local():
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        engine = await get_engine()
        AsyncSessionLocal = sessionmaker(
            autocommit=False,
            autoflush=True,
            bind=engine,
            class_=AsyncSession
        )
    return AsyncSessionLocal

async def get_db():
    AsyncSessionLocal = await get_async_session_local()
    async with AsyncSessionLocal() as session:
        yield session

semaphore = asyncio.Semaphore(25)

async def execute_query(query: str, retries=3):
    for attempt in range(retries):
        try:
            async with semaphore:
                AsyncSessionLocal = await get_async_session_local()
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