from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema
import os
import logging
from sqlalchemy.exc import SQLAlchemyError
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

def execute_ddl(query: str, retries=3):
    """Execute a DDL query with retries."""
    for attempt in range(retries):
        try:
            with engine.begin() as connection:
                connection.execute(text("SET search_path TO data_playground"))
                connection.execute(text(query))
                return True
        except SQLAlchemyError as e:
            logger.error(f"DDL error on attempt {attempt + 1}: {str(e)}")
            if attempt < retries - 1:
                logger.warning(f"Retrying DDL operation...")
                continue
            raise e

def execute_query(query: str, retries=3):
    """Execute a SQL query with retries."""
    for attempt in range(retries):
        try:
            with SessionLocal() as session:
                with session.begin():  # Start a transaction
                    # Set search_path for this query
                    session.execute(text("SET search_path TO data_playground"))
                    result = session.execute(text(query))
                    
                    # Check if this is a SELECT query
                    if query.strip().upper().startswith('SELECT'):
                        rows = result.fetchall()
                        return [dict(row._mapping) for row in rows]
                    return []
                    
        except SQLAlchemyError as e:
            logger.warning(f"Database error on attempt {attempt + 1}: {str(e)}")
            if attempt < retries - 1:
                logger.warning("Retrying...")
                continue
            logger.error("Failed to execute query after multiple attempts.")
            raise e

def get_db():
    """Provides a database session."""
    db = SessionLocal()
    try:
        # Set search_path for this session
        db.execute(text("SET search_path TO data_playground"))
        yield db
    finally:
        db.close()

logger.info("Database connection setup completed.")

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
