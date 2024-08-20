
from datetime import datetime
import httpx

from .new_fake_data_generator_helpers import (
    BASE_URL,
    logger,
    check_api_connection
)


async def call_user_snapshot_api(current_date: datetime):
    """
    Calls the user_snapshot API endpoint with the provided event date.

    Args:
        current_date (datetime): The event date for which the snapshot should be generated.
        client (httpx.AsyncClient): The httpx async client instance to use for making the request.

    Returns:
        dict: The response from the API, or None if the request failed.
    """
    logger.info(f"Attempting to generate {n} users for date {current_date}")
    try:
        if await check_api_connection(BASE_URL):
            async with httpx.AsyncClient() as client:

                try:
                    # Prepare the payload
                    payload = {
                        "event_time": current_date.isoformat(),
                    }

                    # Make the API request
                    logger.info(f"Calling user_snapshot API for current_date: {current_date.isoformat()}")
                    response = await client.post(f"{BASE_URL}/user_snapshot", json=payload)

                    # Handle the response
                    if response.status_code == 200:
                        logger.info(f"User snapshot generated successfully for current_date: {current_date.isoformat()}")
                        return response.json()
                    else:
                        logger.error(f"Failed to generate user snapshot. Status code: {response.status_code}, Response: {response.text}")
                        return None

                except Exception as e:
                    logger.error(f"Exception occurred while calling user_snapshot API: {str(e)}")
                    return None
            
        else:
            logger.warning("API connection failed. Returning None for generated users.")
            return None
    except Exception as e:
        logger.error(f"Error in generate_users: {str(e)}")
        return None