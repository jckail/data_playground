import asyncio
from datetime import datetime, timedelta
import uuid
from typing import List, Dict
from pydantic import BaseModel, Field
import os
import json


from .new_fake_data_generator_helpers import logger
from .odds_maker import OddsMaker
from .user import User, Shop
from .user_actions import generate_users, generate_shops, deactivate_shops, deactivate_users

def make_list_unique(input_list: list):
    unique_list = []
    seen_ids = set()
    for item in input_list:
        if item is not None and item.id not in seen_ids:
            unique_list.append(item)
            seen_ids.add(item.id)
    return unique_list

class ActionCounter(BaseModel):
    users_created: int = 0
    users_deactivated: int = 0
    shops_created: int = 0
    shops_deleted: int = 0
    active_users: int = 0
    active_shops: int = 0


class Batch(BaseModel):
    new_users: List[User] = Field(default_factory=list)
    del_users: List[User] = Field(default_factory=list)
    new_shops: List[Shop] = Field(default_factory=list)
    del_shops: List[Shop] = Field(default_factory=list)
    # with each new batch we will reset the action counter
    # and reset the instance of odds_maker
    active_users: List[Shop] = Field(default_factory=list)
    active_shops: List[Shop] = Field(default_factory=list)
    om : OddsMaker = Field(default_factory=OddsMaker) 
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime = None
    duration: timedelta = None

    def start(self):
        self.start_time = datetime.now()

    def end(self):
        self.end_time = datetime.now()
        self.duration = self.end_time - self.start_time

class BaseDataStore(BaseModel):
    active_users: Dict[uuid.UUID, User] = Field(default_factory=dict)
    active_shops: Dict[uuid.UUID, Shop] = Field(default_factory=dict)
    action_counter: ActionCounter = Field(default_factory=ActionCounter)
    all_action_counter: Dict = Field(default_factory=dict)
    batch: Batch = Field(default_factory=Batch) 
    all_batch: Dict = Field(default_factory=dict)
    
    

    def post_batch_update(self, current_date):
        new_users = make_list_unique(self.batch.new_users)
        del_users = make_list_unique(self.batch.del_users)
        new_shops = make_list_unique(self.batch.new_shops)
        del_shops = make_list_unique(self.batch.del_shops)

        # Update counters
        self.action_counter.users_created += len(new_users)
        self.action_counter.users_deactivated += len(del_users)
        self.action_counter.shops_created += len(new_shops)
        self.action_counter.shops_deleted += len(del_shops)

        # Update active users and shops
        for user in new_users:
            self.active_users[user.id] = user
        for user in del_users:
            self.active_users.pop(user.id, None)

        for shop in new_shops:
            self.active_shops[shop.id] = shop
        for shop in del_shops:
            self.active_shops.pop(shop.id, None)

        self.action_counter.active_users = len(self.active_users)
        self.action_counter.active_shops = len(self.active_shops)

        # Validate counts
        expected_active_users = self.action_counter.users_created - self.action_counter.users_deactivated
        expected_active_shops = self.action_counter.shops_created - self.action_counter.shops_deleted

        if self.action_counter.active_users != expected_active_users:
            logger.warning(f"Mismatch in active users count. Expected: {expected_active_users}, Actual: {self.action_counter.active_users}")

        if self.action_counter.active_shops != expected_active_shops:
            logger.warning(f"Mismatch in active shops count. Expected: {expected_active_shops}, Actual: {self.action_counter.active_shops}")

        # Ensure no negative values
        for attr, value in self.action_counter.__dict__.items():
            if value < 0:
                logger.error(f"Negative value detected for {attr}: {value}")

        # Log batch information
        logger.info(f"Batch Generated {len(new_users)} users")
        logger.info(f"Batch Generated {len(new_shops)} shops")
        logger.info(f"Batch Deactivated {len(del_shops)} shops")
        logger.info(f"Batch Deactivated {len(del_users)} users")

        # Log total counters
        logger.info(f"Total Users created: {self.action_counter.users_created}")
        logger.info(f"Total Users deactivated: {self.action_counter.users_deactivated}")
        logger.info(f"Total Shops created: {self.action_counter.shops_created}")
        logger.info(f"Total Shops deactivated: {self.action_counter.shops_deleted}")
        logger.info(f"Active users: {self.action_counter.active_users}")
        logger.info(f"Active shops: {self.action_counter.active_shops}")

        # Log batch timing information
        logger.info(f"Batch processing time: {self.batch.duration}")

        # Update all_action_counter
        self.all_action_counter[current_date] = {
            **self.action_counter.dict(),
            'processing_time': self.batch.duration.total_seconds()
        }

        # Calculate and log daily changes
        if len(self.all_action_counter) > 1:
            previous_date = max(date for date in self.all_action_counter.keys() if date < current_date)
            previous_counter = self.all_action_counter[previous_date]
            
            logger.info("Daily changes:")
            for key in self.action_counter.__dict__.keys():
                daily_change = self.action_counter.__dict__[key] - previous_counter[key]
                logger.info(f"  {key}: {daily_change}")
            
            time_change = self.all_action_counter[current_date]['processing_time'] - previous_counter['processing_time']
            logger.info(f"  processing_time change: {time_change:.2f} seconds")

        self.all_batch[current_date] = self.batch

        # Log additional metrics
        active_user_list = list(self.active_users.values())
        shops_per_user = [len(user.shops) for user in active_user_list]
        avg_shops_per_user = sum(shops_per_user) / len(active_user_list) if active_user_list else 0

        logger.info(f"Average shops per active user: {avg_shops_per_user:.2f}")
        logger.info(f"Shop distribution:")
        for i in range(max(shops_per_user) + 1):
            count = shops_per_user.count(i)
            percentage = (count / len(active_user_list)) * 100 if active_user_list else 0
            logger.info(f"  Users with {i} shops: {count} ({percentage:.2f}%)")

        # You might want to calculate and log average lifespan of deactivated users and shops here
        # This would require keeping track of creation and deactivation times for each entity


    def create_batch(self):
        self.batch = Batch()
        self.batch.active_users = list(self.active_users.values())
        self.batch.active_shops = list(self.active_shops.values())
        # Reset batch counters
        self.batch.new_users = []
        self.batch.del_users = []
        self.batch.new_shops = []
        self.batch.del_shops = []
        
    
    async def process_day(self, current_date):
        self.create_batch()
        self.batch.start()
        user_count = await self.batch.om.generate_fake_user_growth_amount(self.active_users)

        self.batch.new_users = await generate_users(user_count, current_date)
        # Don't modify self.batch.active_users here, it will be updated in post_batch_update

        new_shop_users = await self.batch.om.generate_fake_shop_growth(self.batch.new_users, self.batch.active_shops)
        self.batch.new_shops = await generate_shops(new_shop_users, user_count, current_date)

        new_shop_users = await self.batch.om.generate_fake_shop_growth(self.batch.active_users, self.batch.active_shops)
        self.batch.new_shops += await generate_shops(new_shop_users, user_count, current_date)

        shop_churn_list = await self.batch.om.generate_fake_shop_churn(self.batch.active_shops)
        within_deactivated_shops = await deactivate_shops(shop_churn_list, user_count, current_date)

        users_to_deactivate = await self.batch.om.generate_fake_user_churn(self.batch.active_users)
        del_users, deactivated_shops = await deactivate_users(users_to_deactivate, user_count, current_date)
        
        self.batch.del_users = del_users
        self.batch.del_shops = [shop for shop in (within_deactivated_shops + deactivated_shops) if shop is not None]

        self.batch.end()

        self.post_batch_update(current_date)




    def analyze_trends(self):
        dates = sorted(self.all_action_counter.keys())
        if len(dates) < 2:
            logger.info("Not enough data to analyze trends")
            return

        first_date = dates[0]
        last_date = dates[-1]
        first_counter = self.all_action_counter[first_date]
        last_counter = self.all_action_counter[last_date]

        # Create the report directory if it doesn't exist
        report_dir = os.path.join(os.getcwd(), "fake_data_reports")
        os.makedirs(report_dir, exist_ok=True)

        # Generate the report filename
        current_time = datetime.now()
        filename_base = current_time.strftime("%Y_%m_%d_%H_%M")
        txt_filename = os.path.join(report_dir, f"{filename_base}.txt")
        json_filename = os.path.join(report_dir, f"{filename_base}.json")

        # Prepare the report content
        report_content = []
        json_content = {"trend_analysis": {}}

        report_content.append(f"Trend analysis from {first_date} to {last_date}:")
        for key in first_counter.keys():
            if key == 'processing_time':
                total_change = last_counter[key] - first_counter[key]
                avg_daily_change = total_change / (len(dates) - 1)
                fastest_day = min((counter[key] for counter in self.all_action_counter.values()))
                slowest_day = max((counter[key] for counter in self.all_action_counter.values()))
                
                report_content.extend([
                    f"  {key}:",
                    f"    Total change: {total_change:.2f} seconds",
                    f"    Average daily change: {avg_daily_change:.2f} seconds",
                    f"    Fastest day: {fastest_day:.2f} seconds",
                    f"    Slowest day: {slowest_day:.2f} seconds"
                ])
                
                json_content["trend_analysis"][key] = {
                    "total_change": total_change,
                    "avg_daily_change": avg_daily_change,
                    "fastest_day": fastest_day,
                    "slowest_day": slowest_day
                }
            else:
                total_change = last_counter[key] - first_counter[key]
                avg_daily_change = total_change / (len(dates) - 1)
                
                report_content.extend([
                    f"  {key}:",
                    f"    Total change: {total_change}",
                    f"    Average daily change: {avg_daily_change:.2f}"
                ])
                
                json_content["trend_analysis"][key] = {
                    "total_change": total_change,
                    "avg_daily_change": avg_daily_change
                }

        # Calculate processing time statistics
        processing_times = [counter['processing_time'] for counter in self.all_action_counter.values()]
        avg_processing_time = sum(processing_times) / len(processing_times)
        min_processing_time = min(processing_times)
        max_processing_time = max(processing_times)

        report_content.extend([
            "Processing time statistics:",
            f"  Average: {avg_processing_time:.2f} seconds",
            f"  Minimum: {min_processing_time:.2f} seconds",
            f"  Maximum: {max_processing_time:.2f} seconds"
        ])

        json_content["processing_time_statistics"] = {
            "average": avg_processing_time,
            "minimum": min_processing_time,
            "maximum": max_processing_time
        }

        # Write the text report
        with open(txt_filename, 'w') as f:
            f.write('\n'.join(report_content))

        # Write the JSON report
        with open(json_filename, 'w') as f:
            json.dump(json_content, f, indent=2)

        logger.info(f"Trend analysis report saved to {txt_filename}")
        logger.info(f"Trend analysis JSON saved to {json_filename}")

        # Log the report content
        for line in report_content:
            logger.info(line)