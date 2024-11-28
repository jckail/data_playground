import os
import sys
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, text
from sqlalchemy import pool

from alembic import context
import alembic_postgresql_enum
from alembic_postgresql_enum import Config

# Configure alembic-postgresql-enum
alembic_postgresql_enum.set_configuration(
    Config(
        add_type_ignore=True  # Ignore type creation in SQLAlchemy models
    )
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("alembic")

# Add the parent directory of 'app' to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import all models explicitly
from app.models import *
from app.models.enums import *
from app.database import SQLALCHEMY_DATABASE_URL, engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL in the Alembic configuration
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# Set schema for all tables
for table in Base.metadata.tables.values():
    table.schema = 'data_playground'

# Get metadata with schema set
target_metadata = Base.metadata

def include_name(name, type_, parent_names):
    """Filter object names"""
    if type_ == "schema":
        # Only include data_playground schema
        return name == "data_playground"
    return True

def include_object(object, name, type_, reflected, compare_to):
    """Only include objects in data_playground schema"""
    # For tables, check schema
    if type_ == "table":
        return getattr(object, "schema", None) == "data_playground"
    
    # For indexes, check if they belong to a data_playground table
    if type_ == "index":
        table_schema = getattr(object.table, "schema", None)
        return table_schema == "data_playground"
    
    # For types/enums, only include those in data_playground schema
    if type_ == "type":
        schema = getattr(object, "schema", None)
        return schema == "data_playground"
    
    # For columns, check if they belong to a data_playground table
    if type_ == "column":
        table_schema = getattr(object.table, "schema", None)
        return table_schema == "data_playground"
    
    return True

def create_schema(connection):
    """Create data_playground schema if it doesn't exist"""
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS data_playground"))
    connection.execute(text("SET search_path TO data_playground"))

def create_enums(connection):
    """Create all enum types before any table creation"""
    logger.info("Creating enum types...")
    
    # Create schema if it doesn't exist
    create_schema(connection)
    
    # Create all enums from enums.py
    enums = [
        (PaymentMethodType, "paymentmethodtype"),
        (PaymentMethodStatus, "paymentmethodstatus"),
        (PaymentStatus, "paymentstatus"),
        (OrderStatus, "orderstatus"),
        (ShippingMethod, "shippingmethod"),
        (PaymentTerms, "paymentterms"),
        (ShopCategory, "shopcategory"),
        (ProductCategory, "productcategory"),
        (ProductStatus, "productstatus"),
        (PromotionType, "promotiontype"),
        (PromotionStatus, "promotionstatus"),
        (PromotionApplicability, "promotionapplicability"),
        (ReviewType, "reviewtype"),
        (ReviewStatus, "reviewstatus"),
        (InventoryChangeType, "inventorychangetype"),
        (EntityType, "entitytype"),
        (EventType, "eventtype")
    ]
    
    for enum_class, enum_name in enums:
        try:
            # Check if enum type exists
            check_sql = f"""
                SELECT EXISTS (
                    SELECT 1 
                    FROM pg_type t 
                    JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace 
                    WHERE t.typname = '{enum_name}' 
                    AND n.nspname = 'data_playground'
                );
            """
            result = connection.execute(text(check_sql)).scalar()
            
            if not result:
                # Create enum if it doesn't exist
                enum_values = [f"'{e.value}'" for e in enum_class]
                create_type_sql = f"""
                    CREATE TYPE data_playground.{enum_name} AS ENUM ({', '.join(enum_values)});
                """
                connection.execute(text(create_type_sql))
                logger.info(f"Created enum type: {enum_name}")
            else:
                logger.info(f"Enum type {enum_name} already exists")
                
        except Exception as e:
            logger.error(f"Error handling enum {enum_name}: {str(e)}")
            raise

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
        # Create schema first
        context.execute("CREATE SCHEMA IF NOT EXISTS data_playground")
        context.execute("SET search_path TO data_playground")
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        with engine.connect() as connection:
            # Create schema first
            create_schema(connection)
            
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_schemas=True,
                version_table="alembic_version",
                version_table_schema="data_playground",
                include_object=include_object,
                include_name=include_name,
                compare_type=True,
                compare_server_default=True,
                transaction_per_migration=True
            )

            logger.info("Starting migrations")
            with context.begin_transaction():
                context.run_migrations()
            logger.info("Migrations completed")

    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
