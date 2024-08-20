from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
import logging
from ..utils.fake_data.new_fake_data_generator_models import (
    BaseDataStore,
    ActionCounter,
)
import pytz
from ..models import OddsMaker
from pydantic import BaseModel, Field
import random

router = APIRouter()

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)


class FakeDataGenerator(BaseModel):
    start_date: datetime = Field(
        default_factory=lambda: (
            datetime.now(pytz.utc) - timedelta(days=14)
        ).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    end_date: datetime = Field(
        default_factory=lambda: (
            datetime.now(pytz.utc) - timedelta(days=1)
        ).replace(hour=23, minute=59, second=59, microsecond=999999)
    )
    max_fake_users_per_day: int = Field(
        default=2000,
        description="Maximum number of fake users that can be created per day",
    )
    max_fake_shops_per_day: int = Field(
        default=1500,
        description="Maximum number of fake shops that can be created per day",
    )
    max_user_growth_rate: float = Field(
        default=0.2, description="Maximum growth rate for users"
    )
    max_shop_growth_rate: float = Field(
        default=0.2, description="Maximum growth rate for shops"
    )
    user_shop_population: float = Field(
        default=0.5, description="Proportion of users who own shops"
    )
    shop_creation_chance: float = Field(
        default=0.8, description="Probability of a user creating a shop"
    )
    user_churn_chance: float = Field(
        default=0.2, description="Probability of a user churning"
    )
    shop_churn_chance: float = Field(
        default=0.3, description="Probability of a shop churning"
    )


    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "start_date": datetime.now(pytz.utc).date() - timedelta(days=15),
                "end_date": datetime.now(pytz.utc).date() - timedelta(days=1),
                "max_fake_users_per_day": 2000,
                "max_fake_shops_per_day": 1500,

                "max_user_growth_rate": 0.2,
                "max_shop_growth_rate": 0.2,

                "user_shop_population": 0.5,
                "shop_creation_chance": 0.8,
                
                "user_churn_chance": 0.2,
                "shop_churn_chance": 0.3,


            }
        }


@router.post("/generate_fake_data")
async def trigger_fake_data_generation(fdg: FakeDataGenerator) -> ActionCounter:
    """
    
    
    """
    logger.info(
        f"Triggering fake data generation for date range {fdg.start_date} to {fdg.end_date}"
    )

    yesterday = datetime.now(pytz.utc).date() - timedelta(minutes=1)

    if fdg.start_date.date() > yesterday:
        logger.warning(
            f"Start date {fdg.start_date} cannot be later than yesterday {yesterday}"
        )
        raise HTTPException(
            status_code=400, detail="Start date cannot be later than yesterday"
        )
    om = OddsMaker(
        max_fake_users_per_day=fdg.max_fake_users_per_day,
        max_fake_shops_per_day=fdg.max_fake_shops_per_day,
        max_user_growth_rate=fdg.max_user_growth_rate,
        max_shop_growth_rate=fdg.max_shop_growth_rate,
        user_shop_population=fdg.user_shop_population,
        shop_creation_chance=fdg.shop_creation_chance,
        user_churn_chance=fdg.user_churn_chance,
        shop_churn_chance=fdg.shop_churn_chance,
        random_seed=42,
        rng = random.Random(42)
    )

    try:

        base = BaseDataStore()

        result_summary = await base.process_date_range(
            fdg.start_date, fdg.end_date, om
        )

    except Exception as e:
        logger.error(f"Data generation failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Data generation failed: {str(e)}"
        )

    logger.info(
        f"Fake data generation completed successfully for {fdg.start_date} to {fdg.end_date}"
    )

    return result_summary



