from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError
import os

# Use psycopg3 instead of psycopg2
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@db/dbname")

# In your database.py
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,    
    pool_size=50,          # Increase the pool size (default is 5)
    max_overflow=20,       # Increase the overflow (default is 10)
    pool_timeout=30,       # Set a suitable timeout value (default is 30)
    pool_recycle=1800,     # Recycle connections after 1800 seconds
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_partition_if_not_exists(db, partition_name, partition_key):
    """
    This function checks if a partition exists and creates it if not.
    """
    try:
        db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF global_events
        FOR VALUES IN ('{partition_key}')
        """))
        db.commit()  # Commit the transaction if the table creation is successful
    except (ProgrammingError, OperationalError) as e:
        db.rollback()  # Rollback if an error occurs to maintain database integrity
        if "relation already exists" not in str(e.orig):
            raise e  # Re-raise if the error is not related to the table already existing
