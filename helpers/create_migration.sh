#!/bin/bash

# Check if migration name is provided
if [ -z "$1" ]; then
    echo "Error: Migration name is required"
    echo "Usage: ./create_migration.sh <migration_name>"
    exit 1
fi

MIGRATION_NAME=$1

# Create Python script to handle partitions
cat > create_partitions.py << EOL
import logging
from app.database import execute_ddl
from alembic.partition_helper import create_initial_partitions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_partitions():
    try:
        logger.info("Creating partitions...")
        create_initial_partitions()
        logger.info("Partitions created successfully")
    except Exception as e:
        logger.error(f"Error creating partitions: {str(e)}")
        raise

if __name__ == "__main__":
    create_partitions()
EOL

echo "Creating migration..."
alembic revision --autogenerate -m "$MIGRATION_NAME"

echo "Upgrading to head..."
alembic upgrade head

echo "Creating partitions..."
python3 create_partitions.py

# Clean up temporary file
rm create_partitions.py

echo "Migration process completed"
