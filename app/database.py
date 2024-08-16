from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError
import os

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
        partition_name = f"{table_name}_{partition_key.replace('-', '_').replace(':', '_')}"
        
        if table_name == "global_events":
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {table_name}
                FOR VALUES IN ('{partition_key}')
            """))
        else:
            if not start_date or not end_date:
                raise ValueError("start_date and end_date are required for RANGE partitioning.")
            
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {table_name}
                FOR VALUES FROM ('{start_date}') TO ('{end_date}')
            """))
        db.commit()  # Commit the transaction if the table creation is successful
    except (ProgrammingError, OperationalError) as e:
        db.rollback()  # Rollback if an error occurs to maintain database integrity
        if "relation already exists" not in str(e.orig):
            raise e  # Re-raise if the error is not related to the table already existing

# Function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()