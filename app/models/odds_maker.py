import logging
from typing import List
from pydantic import BaseModel, Field
import random

logger = logging.getLogger(__name__)

class OddsMaker(BaseModel):
    """
    A class to generate odds and randomize data for user and shop simulations.
    """
    max_fake_users_per_day: int = Field(default=25, description="Maximum number of fake users that can be created per day")
    max_fake_shops_per_day: int = Field(default=20, description="Maximum number of fake shops that can be created per day")
    max_user_growth_rate: float = Field(default=0.2, description="Maximum growth rate for users")
    max_shop_growth_rate: float = Field(default=0.2, description="Maximum growth rate for shops")
    user_shop_population: float = Field(default=0.5, description="Proportion of users who own shops")
    shop_creation_chance: float = Field(default=0.8, description="Probability of a user creating a shop")
    user_churn_chance: float = Field(default=0.2, description="Probability of a user churning")
    shop_churn_chance: float = Field(default=0.3, description="Probability of a shop churning")
    shops_to_generate: int = Field(default_factory=lambda: int(random.uniform(0, 2000)), description="Number of shops to generate")
    random_seed: int = Field(default=42, description="Seed for random number generator")

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize the random generator with the seed
        self.rng = random.Random(self.random_seed)

    async def gen_prop(self, p_list: List, propensity: float, max_value: int = None, r: bool = False) -> int:
        """
        Generate a proportional value based on the given list and propensity.

        :param p_list: The input list
        :param propensity: The propensity value
        :param max_value: The maximum allowed value
        :param r: If True, use a random propensity
        :return: The generated proportional value
        """
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

    async def list_randomizer(self, input_list: List) -> List:
        """
        Randomize the order of elements in the input list.

        :param input_list: The input list to randomize
        :return: The randomized list
        """
        try:
            self.rng.shuffle(input_list)
            return input_list
        except Exception as e:
            logger.error(f"Error in list_randomizer: {str(e)}")
            return input_list

    async def generate_fake_user_growth_amount(self, user_list: List) -> int:
        """
        Generate the number of fake users to grow.

        :param user_list: The current list of users
        :return: The number of fake users to generate
        """
        try:
            growth = await self.gen_prop(user_list, self.max_user_growth_rate, self.max_fake_users_per_day)
            logger.info(f"Generated fake user growth amount: {growth}")
            return growth
        except Exception as e:
            logger.error(f"Error in generate_fake_user_growth_amount: {str(e)}")
            return 0

    async def generate_fake_user_churn(self, user_list: List) -> List:
        """
        Generate a list of users to churn.

        :param user_list: The current list of users
        :return: A list of users to churn
        """
        try:
            num_users_to_del = await self.gen_prop(user_list, self.user_churn_chance, self.max_fake_users_per_day)
            churn_list = self.rng.sample(user_list, num_users_to_del)
            logger.info(f"Generated {len(churn_list)} users to churn")
            return churn_list
        except Exception as e:
            logger.error(f"Error in generate_fake_user_churn: {str(e)}")
            return []

    async def generate_fake_shop_growth(self, user_list: List, shop_list: List) -> List:
        """
        Generate a list of users who will create new shops.

        :param user_list: The current list of users
        :param shop_list: The current list of shops
        :return: A list of users who will create new shops
        """
        try:
            num_shops_to_create = await self.gen_prop(shop_list, self.max_shop_growth_rate, self.max_fake_shops_per_day)
            shop_creators = self.rng.sample(user_list, num_shops_to_create)
            logger.info(f"Generated {len(shop_creators)} users to create new shops")
            return shop_creators
        except Exception as e:
            logger.error(f"Error in generate_fake_shop_growth: {str(e)}")
            return []

    async def generate_fake_shop_churn(self, shop_list: List) -> List:
        """
        Generate a list of shops to churn.

        :param shop_list: The current list of shops
        :return: A list of shops to churn
        """
        try:
            num_shops_to_del = await self.gen_prop(shop_list, self.shop_churn_chance, self.max_fake_shops_per_day)
            churn_list = self.rng.sample(shop_list, num_shops_to_del)
            logger.info(f"Generated {len(churn_list)} shops to churn")
            return churn_list
        except Exception as e:
            logger.error(f"Error in generate_fake_shop_churn: {str(e)}")
            return []

    def set_random_seed(self, seed: int):
        """Set the random seed for this OddsMaker instance."""
        self.random_seed = seed
        random.seed(self.random_seed)