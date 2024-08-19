import asyncio
import logging
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
logger = logging.getLogger(__name__)

async def is_database_ready(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database not ready: {str(e)}")
        return False

def retry_with_backoff(max_retries=5, initial_wait=1, backoff_factor=2):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            wait = initial_wait
            while retries < max_retries:
                try:
                    db = kwargs.get('db') or args[0]  # Assuming db is the first arg or a kwarg
                    if not await is_database_ready(db):
                        raise Exception("Database not ready")
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Max retries reached. Last error: {str(e)}")
                        raise
                    logger.warning(f"Attempt {retries} failed. Retrying in {wait} seconds. Error: {str(e)}")
                    await asyncio.sleep(wait)
                    wait *= backoff_factor
        return wrapper
    return decorator

