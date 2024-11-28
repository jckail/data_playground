import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool, MetaData, DDL, event
from sqlalchemy.schema import CreateSchema

from alembic import context

# Add the parent directory of 'app' to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import all models explicitly
from app.models import *
from app.database import SQLALCHEMY_DATABASE_URL

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL in the Alembic configuration
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# Create a metadata object specifically for our tables
def combine_metadata(*args):
    m = MetaData()
    for metadata in args:
        for t in metadata.tables.values():
            t.tometadata(m)
    return m

# Combine all model metadata
target_metadata = Base.metadata

# List of tables that belong to our application with their schemas
OUR_TABLES = {
    'data_playground.global_entities',
    'data_playground.global_events',
    'data_playground.odds_maker',
    'data_playground.payments',
    'data_playground.request_response_logs',
    'data_playground.shops',
    'data_playground.invoices',
    'data_playground.users',
    'data_playground.shop_products',
    'data_playground.shop_orders',
    'data_playground.shop_order_items',
    'data_playground.shop_reviews',
    'data_playground.shop_review_votes',
    'data_playground.shop_inventory_logs',
    'data_playground.shop_promotions',
    'data_playground.shop_promotion_usages',
    'data_playground.payment_methods',
    'data_playground.shop_order_payments',
    # Metric tables
    'data_playground.metrics_hourly',
    'data_playground.metrics_daily',
    'data_playground.shop_metrics_hourly',
    'data_playground.shop_metrics_daily',
    'data_playground.shop_product_metrics_hourly',
    'data_playground.shop_product_metrics_daily'
}

def include_object(object, name, type_, reflected, compare_to):
    # Always include enums in data_playground schema
    if type_ == "type":
        # Set schema for enum types
        if hasattr(object, 'schema'):
            object.schema = 'data_playground'
        return True
        
    if type_ == "table":
        # Get schema and table name
        schema = object.schema if hasattr(object, 'schema') else 'data_playground'
        full_name = f"{schema}.{name}"
        return full_name in OUR_TABLES
    
    if type_ == "index":
        # Only include indexes if they're on our tables
        if hasattr(object, 'table'):
            schema = object.table.schema if hasattr(object.table, 'schema') else 'data_playground'
            table_full_name = f"{schema}.{object.table.name}"
            return table_full_name in OUR_TABLES
    
    return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        version_table_schema='data_playground',
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    try:
        # Get alembic section config
        configuration = config.get_section(config.config_ini_section)
        
        # Add SSL mode
        configuration["sqlalchemy.connect_args"] = {
            'sslmode': 'require',
            'connect_timeout': 10
        }

        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            # Create schema if it doesn't exist
            connection.execute(CreateSchema('data_playground', if_not_exists=True))
            # Set search_path to ensure types are created in data_playground schema
            connection.execute(DDL('SET search_path TO data_playground'))

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_object=include_object,
                compare_type=True,
                compare_server_default=True,
                include_schemas=True,
                version_table_schema='data_playground',
            )

            with context.begin_transaction():
                context.run_migrations()

    except Exception as e:
        print(f"Error during migration: {e}")
        raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
