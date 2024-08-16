from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError
import os
from datetime import  timedelta , datetime
import pytz
from dateutil.parser import parse
from fastapi import HTTPException


# Use psycopg3 instead of psycopg2
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://user:password@localhost/dbname"  # Update with your local database details
)

# Create the SQLAlchemy engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,    
    pool_size=50,          # Increase the pool size (default is 5)
    max_overflow=20,       # Increase the overflow (default is 10)
    pool_timeout=30,       # Set a suitable timeout value (default is 30)
    pool_recycle=1800,     # Recycle connections after 1800 seconds
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to create partitions dynamically
def create_partition_if_not_exists(db, table_name, partition_key, start_date=None, end_date=None):
    """
    This function checks if a partition exists and creates it if not.
    - For global_events, it uses LIST partitioning with a partition_key.
    - For other tables like users, shops, user_invoices, and payments, it uses RANGE partitioning with a date range.
    """
    try:
        # Sanitize partition_key to be safe for use in table name
        
        partition_name = f"{table_name}_p_{partition_key.replace('-', '_').replace(':', '_')}"
        if table_name == "global_events":
            
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {table_name}
                FOR VALUES IN ('{partition_key}')
            """))
            db.commit()

        else:
            partition_name = f"{table_name}_p_{partition_key.replace('-', '_').replace(':', '_')}"
            #partition_name = f"{table_name}_p_{partition_key.strftime('%Y_%m_%d')}"
            # Ensure start_date and end_date are calculated properly
            if not start_date or not end_date:
                start_date = partition_key
                end_date = start_date + timedelta(days=1)  # Adjust end_date to include the partition_key day
            
            # Convert dates to string format
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            


            # Debugging: log the partition creation details
            print(f"Creating partition: {partition_name} for range {start_date_str} to {end_date_str}")

            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {table_name}
                FOR VALUES FROM ('{start_date_str}') TO ('{end_date_str}')
            """))
            db.commit()  # Commit the transaction if the table creation is successful
            
        return partition_name 
        
    except (ProgrammingError, OperationalError) as e:
        db.rollback()  # Rollback if an error occurs to maintain database integrity
        if "relation already exists" not in str(e.orig):
            raise e  # Re-raise if the error is not related to the table already existing


# Function to create partitions dynamically
def new_create_partition_if_not_exists(db, table_name, partition_key):
    if not isinstance(partition_key, datetime):
        print(f"Invalid Datetime event_time type:{partition_key} --> {type(partition_key)}")
        partition_key = datetime.utcnow()
    
    if table_name == "global_events":
        partition_key = partition_key.strftime("%Y-%m-%d:%H:00")
    else:
        partition_key = partition_key.strftime("%Y-%m-%d")

    partition_name = f"{table_name}_p_{partition_key.replace('-', '_').replace(':', '_')}"
    
    print(partition_key, partition_name)
    db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {table_name}
        FOR VALUES IN ('{partition_key}')
    """))
    db.commit()
    return partition_key



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