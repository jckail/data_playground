import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "postgresql+psycopg://user:password@db/dbname"

# Add retry logic for database connection
max_retries = 5
retry_delay = 5

for i in range(max_retries):
    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URL)
        engine.connect()
        break
    except Exception as e:
        if i < max_retries - 1:
            print(f"Database connection attempt {i+1} failed. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("Failed to connect to the database after multiple attempts.")
            raise e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()