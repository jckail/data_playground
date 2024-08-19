import sys
import os
import asyncio
import random
from datetime import datetime, timedelta
import pytz

from typing import List, Dict
from faker import Faker
import httpx
import time






async def check_api_connection():
    logger.info(f"Checking API connection to {BASE_URL}")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(BASE_URL)
            logger.info(f"API check status: {response.status_code}")
            return response.status_code == 200
        except httpx.RequestError as e:
            logger.error(f"Error connecting to API: {e}")
            return False




