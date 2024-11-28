import os
import sys
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, text, pool
from alembic import context
import alembic_postgresql_enum
from alembic_postgresql_enum import Config

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import partition helper from app.utils
from app.utils.partition_helper import initialize_table

# Configure alembic-postgresql-enum to handle enum operations
alembic_postgresql_enum.set_configuration(
    Config(
        add_type_ignore=True  # Let the library handle enum creation
    )
)

# Import models and database configuration
from app.models import *
from app.models.enums import *
from app.database import SQLALCHEMY_DATABASE_URL, engine


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alembic")

# Alembic Config
config = context.config
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

def include_name(name, type_, parent_names):
    """Filter object names to only include data_playground schema"""
    if type_ == "schema":
        return name == "data_playground"
    return True

def include_object(object, name, type_, reflected, compare_to):
    """Filter objects to only include those in data_playground schema"""
    if type_ == "table":
        return getattr(object, "schema", None) == "data_playground"
    elif type_ == "index":
        return getattr(object.table, "schema", None) == "data_playground"
    elif type_ == "type":
        return getattr(object, "schema", None) == "data_playground"
    elif type_ == "column":
        return getattr(object.table, "schema", None) == "data_playground"
    return True

def get_partitioned_tables():
    """Get list of tables that need partitioning"""
    logger.info("Scanning for partitioned tables...")
    tables = []
    for table in target_metadata.tables.values():
        if 'postgresql_partition_by' in table.kwargs:
            tables.append(table.name)
            logger.info(f"Found partitioned table: {table.name}")
    logger.info(f"Total partitioned tables found: {len(tables)}")
    return tables

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table="alembic_version",
        version_table_schema="data_playground",
        include_object=include_object,
        include_name=include_name,
        compare_type=True,
        compare_server_default=True
    )

    with context.begin_transaction():
        context.execute(text("SET search_path TO data_playground"))
        context.run_migrations()
        
        # Initialize partitions for all partitioned tables
        partitioned_tables = get_partitioned_tables()
        if partitioned_tables:
            logger.info("Creating partitions for tables in offline mode...")
            with engine.connect() as connection:
                initialize_table(connection, partitioned_tables)
        else:
            logger.info("No partitioned tables found to initialize")

def run_migrations_online() -> None:
    """Run migrations in 'online' mode"""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table="alembic_version",
            version_table_schema="data_playground",
            include_object=include_object,
            include_name=include_name,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.execute(text("SET search_path TO data_playground"))
            context.run_migrations()
            
            # Initialize partitions for all partitioned tables
            #TODO:  Fix this later
            # partitioned_tables = get_partitioned_tables()
            # if partitioned_tables:
            #     logger.info("Creating partitions for tables in online mode...")
            #     initialize_table(connection, partitioned_tables)
            # else:
            #     logger.info("No partitioned tables found to initialize")

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
