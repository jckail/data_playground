import asyncio
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from db import  get_db

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("request_response_logger")

# Limit the number of concurrent database queries
semaphore = asyncio.Semaphore(10)

async def execute_query(query: str, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            async with semaphore:
                async for session in get_db():
                    async with session.begin():
                        result = await session.execute(text(query))
                        rows = result.fetchall()
                        return [dict(row._mapping) for row in rows]
        except SQLAlchemyError as e:
            logger.warning(f"Query failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error(f"Query failed after {max_retries} attempts: {e}")
                return []  # Return an empty list instead of raising an exception
    return []  # This line should never be reached, but it's here for completeness


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

def get_sankey_query(start_date, end_date):
    return f"""
WITH date_range AS (
    SELECT 
        '{start_date}'::date AS start_date,
        '{end_date}'::date AS end_date
),
user_events AS (
    SELECT 
        (event_metadata->>'user_id')::uuid AS user_id,
        event_metadata->>'email' AS email,
        CASE 
            WHEN event_type = 'user_account_creation' THEN 'User Created'
            WHEN event_type = 'user_delete_account' THEN 'User Deleted'
        END AS event_type,
        event_time::timestamp AS event_time
    FROM global_events, date_range
    WHERE event_type IN ('user_account_creation', 'user_delete_account')
    AND event_time::date BETWEEN date_range.start_date AND date_range.end_date
),
shop_events AS (
    SELECT 
        (event_metadata->>'shop_id')::uuid AS shop_id,
        (event_metadata->>'shop_owner_id')::uuid AS user_id,
        event_metadata->>'shop_name' AS shop_name,
        CASE 
            WHEN event_type = 'user_shop_create' THEN 'Shop Created'
            WHEN event_type = 'user_shop_delete' THEN 'Shop Deleted'
        END AS event_type,
        event_time::timestamp AS event_time
    FROM global_events, date_range
    WHERE event_type IN ('user_shop_create', 'user_shop_delete')
    AND event_time::date BETWEEN date_range.start_date AND date_range.end_date
),
combined_events AS (
    SELECT user_id, email, event_type, event_time, NULL::uuid AS shop_id, NULL AS shop_name FROM user_events
    UNION ALL
    SELECT user_id, NULL AS email, event_type, event_time, shop_id, shop_name FROM shop_events
),
user_status AS (
    SELECT 
        user_id,
        MAX(email) AS email,
        CASE 
            WHEN MAX(CASE WHEN event_type = 'User Deleted' THEN event_time END) IS NULL THEN 'Active'
            ELSE 'Deleted'
        END AS status
    FROM combined_events
    GROUP BY user_id
),
shop_status AS (
    SELECT 
        shop_id,
        user_id,
        MAX(shop_name) AS shop_name,
        CASE 
            WHEN MAX(CASE WHEN event_type = 'Shop Deleted' THEN event_time END) IS NULL THEN 'Active'
            ELSE 'Deleted'
        END AS status
    FROM combined_events
    WHERE shop_id IS NOT NULL
    GROUP BY shop_id, user_id
)
SELECT 
    'Users' AS source,
    CASE 
        WHEN s.shop_id IS NOT NULL THEN 'Shops'
        ELSE u.status
    END AS target,
    COUNT(DISTINCT u.user_id) AS value
FROM user_status u
LEFT JOIN shop_status s ON u.user_id = s.user_id
GROUP BY source, target

UNION ALL

SELECT 
    'Shops' AS source,
    s.status AS target,
    COUNT(DISTINCT s.shop_id) AS value
FROM shop_status s
GROUP BY source, target
"""