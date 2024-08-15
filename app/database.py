from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Use psycopg3 instead of psycopg2
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@db/dbname")


engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)