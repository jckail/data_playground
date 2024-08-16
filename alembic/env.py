import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the parent directory of 'app' to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import your models
from app.models import Base
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

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def exclude_partitions(autogen_context, tablename):
    def include_object(object, name, type_, reflected, compare_to):
        if type_ == "table" and name.startswith(f"{tablename}_p_"):
            return False
        return True
    return include_object

class PartitionedTableComparator:
    def __init__(self, autogen_context, partition_tables):
        self.autogen_context = autogen_context
        self.partition_tables = partition_tables

    def render_item(self, type_, obj, autogen_context):
        if type_ == "table" and obj.name in self.partition_tables:
            return None
        return False

def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return not (name.startswith("global_events_p_") or name.startswith("shops_p_"))
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
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
            render_item=PartitionedTableComparator(context, ["global_events", "shops"]).render_item,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()