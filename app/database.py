from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from datetime import datetime
import pytz
from dateutil.parser import parse
from fastapi import HTTPException
from dotenv import load_dotenv

logger = logging.getLogger("streamlit_app")
logging.basicConfig(level=logging.INFO)

load_dotenv()

# Database connection setup
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres"
)

# Get connection pool settings from environment variables
POOL_SIZE = int(os.getenv("POOL_SIZE", 20))
MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", 10))
POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", 30))
POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", 1800))

# Create the engine with SSL required and timeout settings
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={
        'sslmode': 'require',
        'connect_timeout': 10,
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5
    }
)

# Create sessionmaker
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

def get_db():
    """Provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

logger.info("Database connection setup completed.")

def execute_query(query: str, retries=3):
    """Execute a SQL query with retries on interface errors."""
    for attempt in range(retries):
        try:
            with SessionLocal() as session:
                with session.begin():  # Start a transaction
                    result = session.execute(text(query))
                    rows = result.fetchall()
                    return [dict(row._mapping) for row in rows]
        except SQLAlchemyError as e:
            if attempt < retries - 1:
                logger.warning(f"Database error on attempt {attempt + 1}, retrying...")
                continue
            logger.error("Failed to execute query after multiple attempts.")
            raise e

def parse_event_time(event_time):
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
