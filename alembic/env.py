import os
import sys
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool, MetaData, DDL, event, text
from sqlalchemy.schema import CreateSchema

from alembic import context

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("alembic")

# Add the parent directory of 'app' to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import all models explicitly
from app.models import *
from app.models.enums import *
from app.database import SQLALCHEMY_DATABASE_URL, engine, execute_ddl

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL in the Alembic configuration
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# Combine all model metadata
target_metadata = Base.metadata

# Prevent SQLAlchemy from auto-creating enum types
for table in target_metadata.tables.values():
    for column in table.columns:
        if hasattr(column.type, 'create_type'):
            column.type.create_type = False

def create_enums(connection):
    """Create all enum types before any table creation"""
    logger.info("Creating enum types...")
    
    # Create schema if it doesn't exist
    connection.execute(text("CREATE SCHEMA IF NOT EXISTS data_playground"))
    
    # Set search path to data_playground schema
    connection.execute(text("SET search_path TO data_playground"))
    
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
        (EntityType, "entitytype")
    ]
    
    for enum_class, enum_name in enums:
        try:
            # First check if the enum type exists
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
                # Enum doesn't exist, create it
                enum_values = [f"'{e.value}'" for e in enum_class]
                create_type_sql = f"""
                    CREATE TYPE data_playground.{enum_name} AS ENUM ({', '.join(enum_values)});
                """
                connection.execute(text(create_type_sql))
                logger.info(f"Created enum type: {enum_name}")
            else:
                logger.info(f"Enum type {enum_name} already exists, skipping creation")
                
        except Exception as e:
            logger.error(f"Error handling enum {enum_name}: {str(e)}")
            raise

def include_object(object, name, type_, reflected, compare_to):
    """Determine which database objects to include in the migration."""
    # Only include objects in data_playground schema
    if hasattr(object, 'schema'):
        return object.schema == 'data_playground'
    return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema='data_playground',
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        with engine.connect() as connection:
            # Create enums first
            # create_enums(connection)
            
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_schemas=True,
                version_table_schema='data_playground',
                include_object=include_object,
                compare_type=True,
                compare_server_default=True,
                transaction_per_migration=True,
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
