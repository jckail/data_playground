from .. routes.admin import create_rollups
import logging
from datetime import datetime
from ..database import get_db
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_rollups_task():
    # Add the logic for rollups
    try:
        # Here, you'd call your rollup logic or endpoint, like this:
        create_rollups(background_tasks=None, start_date=datetime.now(), end_date=datetime.now(), db=get_db())
    except Exception as e:
        logger.error(f"Error running rollups task: {str(e)}")