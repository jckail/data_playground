from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError, OperationalError
from datetime import datetime, timedelta
import logging

# Set up the logger
logger = logging.getLogger("partition_logger")
logging.basicConfig(level=logging.INFO)

# Use the synchronous SQLAlchemy engine and session
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://user:password@db/dbname"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=250,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def generate_partition_name(tablename, partition_key):
    return f"{tablename}_p_{partition_key.replace('-', '_').replace(':', '_')}"

def create_partition(session, tablename, partition_key, partition_type="hourly"):
    partition_name = generate_partition_name(tablename, partition_key)
    try:
        if partition_type == "hourly":
            session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {tablename}
                FOR VALUES IN ('{partition_key}')
            """))
        elif partition_type == "daily":
            next_partition = (datetime.fromisoformat(partition_key) + timedelta(days=1)).strftime("%Y-%m-%d")
            session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {tablename}
                FOR VALUES FROM ('{partition_key}') TO ('{next_partition}')
            """))
        else:
            raise ValueError("Invalid partition type")

        session.commit()
        logger.info(f"Created partition {partition_name} for {partition_key}")
    except (ProgrammingError, OperationalError) as e:
        logger.error(f"Error creating partition {partition_name}: {str(e)}", exc_info=True)
        session.rollback()

def create_partitions_for_two_years():
    session = SessionLocal()
    try:
        end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=365)
        current_date = start_date

        while current_date <= end_date:
            for hour in range(24):
                partition_key = current_date.replace(hour=hour).strftime("%Y-%m-%dT%H:00:00")
                create_partition(session, "global_events", partition_key, partition_type="hourly")
            current_date += timedelta(days=1)
            logger.info(f"Completed partitions for {current_date.date()}")
    finally:
        session.close()

if __name__ == "__main__":
    create_partitions_for_two_years()
