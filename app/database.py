from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError
import os
from datetime import  timedelta

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



# Function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()