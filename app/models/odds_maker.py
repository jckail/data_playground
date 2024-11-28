import logging
from sqlalchemy import Column, Integer, Float, String
from .base import Base
import random

logger = logging.getLogger(__name__)

class OddsMaker(Base):
    """
    A class to generate odds and randomize data for fake user and shop simulations.
    """
    __tablename__ = 'odds_maker'

    id = Column(Integer, primary_key=True)
    max_fake_users_per_day = Column(Integer, default=500)
    max_fake_shops_per_day = Column(Integer, default=150)
    max_user_growth_rate = Column(Float, default=0.2)
    max_shop_growth_rate = Column(Float, default=0.2)
    shop_population = Column(Float, default=0.5)
    shop_creation_chance = Column(Float, default=0.8)
    user_churn_chance = Column(Float, default=0.2)
    shop_churn_chance = Column(Float, default=0.3)
    shops_to_generate = Column(Integer, default=1000)
    random_seed = Column(Integer, default=42)

    __table_args__ = {
        'schema': 'data_playground'
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rng = None
        self.set_random_seed(kwargs.get('random_seed', 42))

    @property
    def rng(self):
        """Get the random number generator instance."""
        if not self._rng:
            self._rng = random.Random(self.random_seed)
        return self._rng

    async def gen_prop(self, p_list: list, propensity: float, max_value: int = None, r: bool = False) -> int:
        """Generate a proportional value based on the given list and propensity."""
        try:
            population = len(p_list)
            if population == 0:
                return max_value or 0

            if r:
                propensity = self.rng.uniform(0, propensity)

            generated_value = int(population * propensity)
            if max_value is not None:
                return min(generated_value, max_value)
            return generated_value
        except Exception as e:
            logger.error(f"Error in gen_prop: {str(e)}")
            return 0

    async def list_randomizer(self, input_list: list) -> list:
        """Randomize the order of elements in the input list."""
        try:
            input_list_copy = input_list.copy()
            self.rng.shuffle(input_list_copy)
            return input_list_copy
        except Exception as e:
            logger.error(f"Error in list_randomizer: {str(e)}")
            return input_list

    async def generate_fake_user_growth_rate(self) -> float:
        """Generate a small positive growth rate for fake users."""
        return self.rng.uniform(0.001, self.max_user_growth_rate)

    async def generate_fake_user_churn_rate(self) -> float:
        """Generate a small churn rate for fake users."""
        return self.rng.uniform(0.0005, self.user_churn_chance)

    async def generate_fake_user_growth_amount(self, fake_user_list: list) -> int:
        """Generate the amount of fake user growth."""
        try:
            if not fake_user_list:
                return max(1, int(self.max_fake_users_per_day * self.rng.random()))
            growth = await self.gen_prop(fake_user_list, self.max_user_growth_rate, self.max_fake_users_per_day)
            logger.info(f"Generated fake user growth amount: {growth}")
            return growth
        except Exception as e:
            logger.error(f"Error in generate_fake_user_growth_amount: {str(e)}")
            return 1

    async def generate_fake_user_churn(self, fake_user_list: list) -> list:
        """Generate a list of fake users to churn."""
        try:
            num_users_to_del = int(len(fake_user_list) * self.user_churn_chance)
            max_churn = min(num_users_to_del, int(len(fake_user_list) * 0.1))
            churn_list = self.rng.sample(fake_user_list, max_churn)
            logger.info(f"Generated {len(churn_list)} fake users to churn")
            return churn_list
        except Exception as e:
            logger.error(f"Error in generate_fake_user_churn: {str(e)}")
            return []

    async def generate_fake_shop_growth(self, fake_user_list: list, fake_shop_list: list) -> list:
        """Generate a list of fake users who will create new shops."""
        try:
            num_shops_to_create = await self.gen_prop(fake_shop_list, self.max_shop_growth_rate, self.max_fake_shops_per_day)
            shop_creators = self.rng.sample(fake_user_list, num_shops_to_create)
            logger.info(f"Generated {len(shop_creators)} fake users to create new shops")
            return shop_creators
        except Exception as e:
            logger.error(f"Error in generate_fake_shop_growth: {str(e)}")
            return []

    async def generate_fake_shop_churn(self, fake_shop_list: list) -> list:
        """Generate a list of fake shops to churn."""
        try:
            num_shops_to_del = int(len(fake_shop_list) * self.shop_churn_chance)
            max_churn = min(num_shops_to_del, int(len(fake_shop_list) * 0.1))
            churn_list = self.rng.sample(fake_shop_list, max_churn)
            logger.info(f"Generated {len(churn_list)} fake shops to churn")
            return churn_list
        except Exception as e:
            logger.error(f"Error in generate_fake_shop_churn: {str(e)}")
            return []

    def set_random_seed(self, seed: int):
        """Set the random seed for this OddsMaker instance."""
        self.random_seed = seed
        self._rng = random.Random(self.random_seed)
