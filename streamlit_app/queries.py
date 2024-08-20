import asyncio
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy import text
from db import AsyncSessionLocal

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("request_response_logger")

# Limit the number of concurrent database queries
semaphore = asyncio.Semaphore(10)

async def execute_query(query: str, retries=3):
    for attempt in range(retries):
        try:
            async with semaphore:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        result = await session.execute(text(query))
                        rows = result.fetchall()
                        return [dict(row._mapping) for row in rows]
        except (InterfaceError, OperationalError) as e:
            if attempt < retries - 1:
                logger.warning(f"Query failed (attempt {attempt + 1}/{retries}), retrying...")
                await asyncio.sleep(1)
                continue
            else:
                logger.error(f"Query failed after {retries} attempts: {e}")
                raise e

# Define your SQL queries
users_query = "SELECT created_time::timestamp::date AS partition_key,count(distinct id) b FROM users GROUP BY  created_time::timestamp::date ORDER BY 1;"
shops_query = "SELECT created_time::timestamp::date AS partition_key,count(distinct id) b FROM shops GROUP BY  created_time::timestamp::date ORDER BY 1;"
events_query = """
    SELECT event_time::timestamp::date AS event_date,
           event_type,
           count(distinct event_id) as count
    FROM global_events
    GROUP BY event_date, event_type
    ORDER BY event_date;
"""
request_response_logs_query = """
    WITH recent_hour AS (
        SELECT date_trunc('hour', MAX(event_time)) AS max_hour
        FROM request_response_logs
    )
    SELECT date_trunc('minute', event_time) AS minute,
           status_code,
           count(*) as count
    FROM request_response_logs, recent_hour
    WHERE event_time >= recent_hour.max_hour
      AND event_time < recent_hour.max_hour + INTERVAL '1 hour'
    GROUP BY minute, status_code
    ORDER BY minute;
"""
