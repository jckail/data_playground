import os
import sys
import logging

# Add the project root to PYTHONPATH
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
alembic_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([project_root, alembic_dir])

from app.database import execute_ddl, execute_query
import partition_helper  # Direct import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_all_tables():
    """Drop all tables in data_playground schema"""
    logger.info("Dropping all tables...")
    
    # Get all tables
    tables = execute_query("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'data_playground'
        AND table_type = 'BASE TABLE'
    """)
    
    # Drop each table
    for table in tables:
        table_name = table['table_name']
        logger.info(f"Dropping table {table_name}")
        execute_ddl(f"DROP TABLE IF EXISTS data_playground.{table_name} CASCADE")

def drop_all_types():
    """Drop all custom types in data_playground schema"""
    logger.info("Dropping all custom types...")
    
    # Get all enum types
    types = execute_query("""
        SELECT t.typname
        FROM pg_type t
        JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'data_playground'
        AND t.typtype = 'e'
    """)
    
    # Drop each type
    for type_info in types:
        type_name = type_info['typname']
        logger.info(f"Dropping type {type_name}")
        execute_ddl(f"DROP TYPE IF EXISTS data_playground.{type_name} CASCADE")

def drop_schema():
    """Drop and recreate the data_playground schema"""
    logger.info("Dropping and recreating schema...")
    execute_ddl("DROP SCHEMA IF EXISTS data_playground CASCADE")
    execute_ddl("CREATE SCHEMA data_playground")

def run_migrations():
    """Run alembic migrations"""
    logger.info("Running migrations...")
    import subprocess
    result = subprocess.run(['alembic', 'upgrade', 'head'], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Migration failed: {result.stderr}")
        raise Exception("Migration failed")
    logger.info("Migrations completed successfully")

def setup_partitions():
    """Create partitions for all tables"""
    logger.info("Setting up table partitions...")
    try:
        partition_helper.create_initial_partitions()
        logger.info("Table partitions created successfully")
    except Exception as e:
        logger.error(f"Error creating partitions: {str(e)}")
        raise

def main():
    """Main function to restart database"""
    try:
        logger.info("Starting database restart process...")
        
        # Drop everything
        drop_all_tables()
        drop_all_types()
        drop_schema()
        
        # Run migrations to create tables and enums
        run_migrations()
        
        # Create partitions for all tables
        setup_partitions()
        
        logger.info("Database restart completed successfully")
        
    except Exception as e:
        logger.error(f"Error during database restart: {str(e)}")
        raise

if __name__ == "__main__":
    main()
