from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError
import os
from datetime import timedelta, datetime
import pytz
from dateutil.parser import parse
from fastapi import HTTPException
import psycopg2
import psycopg2.extras
import logging

logger = logging.getLogger("request_response_logger")
logging.basicConfig(level=logging.INFO)

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://user:password@localhost/dbname"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,    
    pool_size=50,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def parse_event_time(event_time):
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
            event_time =  parse(event_time)
        elif event_time is None:
            event_time=  datetime.utcnow().replace(tzinfo=pytz.UTC)
        elif isinstance(event_time, datetime):
            pass
        else:
            raise ValueError("event_time must be a datetime object or a valid datetime string")
        
        return datetime.fromisoformat(event_time.isoformat())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format for event_time: {e}")

# Function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_connection():
    return psycopg2.connect(SQLALCHEMY_DATABASE_URL)

def execute_query(query):
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query)
        results = cur.fetchall()
    conn.close()
    return results