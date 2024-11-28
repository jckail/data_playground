import os
from sqlalchemy import create_engine, text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
            
        logger.info("Creating database engine...")
        engine = create_engine(database_url)
        
        # Test connection and schema access
        with engine.connect() as conn:
            logger.info("Testing connection...")
            
            # Test basic connection
            result = conn.execute(text("SELECT current_database(), current_user, session_user"))
            db, curr_user, sess_user = result.fetchone()
            logger.info(f"Connected to database: {db}")
            logger.info(f"Current user: {curr_user}")
            logger.info(f"Session user: {sess_user}")
            
            # Test schema access
            logger.info("Testing schema access...")
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = 'data_playground'
            """))
            if result.fetchone():
                logger.info("data_playground schema exists")
            else:
                logger.info("data_playground schema does not exist")
            
            # Test schema permissions
            logger.info("Testing schema permissions...")
            try:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS data_playground"))
                logger.info("Can create schema")
            except Exception as e:
                logger.warning(f"Cannot create schema: {str(e)}")
            
            try:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS data_playground.test_table (
                        id serial PRIMARY KEY,
                        name text
                    )
                """))
                logger.info("Can create tables")
                
                # Clean up test table
                conn.execute(text("DROP TABLE IF EXISTS data_playground.test_table"))
            except Exception as e:
                logger.warning(f"Cannot create tables: {str(e)}")
            
        logger.info("Connection test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
