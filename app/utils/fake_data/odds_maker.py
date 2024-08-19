from datetime import datetime
from typing import List
from pydantic import BaseModel, Field
import random


class OddsMaker(BaseModel):
    max_fake_users_per_day: int = Field(default=1200)
    max_fake_shops_per_day: int = Field(default=2000)
    max_user_growth_rate: float = Field(default=0.2)
    max_shop_growth_rate: float = Field(default=0.2)
    user_shop_population: float = Field(default=0.5)
    shop_creation_chance: float = Field(default=0.8)
    user_churn_chance: float = Field(default=0.2)
    shop_churn_chance: float = Field(default=0.3)
    shops_to_generate: int = Field(default_factory=lambda: int(random.uniform(0, 2000)))

    async def gen_prop(self, p_list: List, propensity: float, max_value: int = None, r: bool = False) -> int:
        population = len(p_list)
        if population == 0:
            return max_value or 0

        if not max_value:
            max_value = population

        if r:
            propensity = random.uniform(0, propensity)

        return min(int(population * propensity), max_value)
    
    async def list_randomizer(self, input_list: List) -> List:
        for _ in range(int(random.uniform(1, 3))):
            random.shuffle(input_list)
        return input_list

    async def generate_fake_user_growth_amount(self, user_list: List) -> int:
        return await self.gen_prop(user_list, self.max_user_growth_rate, self.max_fake_users_per_day)
    
    async def generate_fake_shop_growth(self, user_list: List, shop_list: List) -> List:
        num_shops_to_create = await self.gen_prop(shop_list, self.max_shop_growth_rate, self.max_fake_shops_per_day)
        user_list = await self.list_randomizer(user_list)
        return user_list[:num_shops_to_create]
    
    async def generate_fake_shop_churn(self, shop_list: List) -> List:
        num_shops_to_del = await self.gen_prop(shop_list, self.shop_churn_chance, self.max_fake_shops_per_day)
        shop_list = await self.list_randomizer(shop_list)
        return shop_list[:num_shops_to_del]
