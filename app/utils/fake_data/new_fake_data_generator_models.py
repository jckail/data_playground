from datetime import datetime, timedelta
import uuid
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import os
import json
import logging
import asyncio
from ...models.odds_maker import OddsMaker
from .user import User, Shop
from .user_actions import generate_users, generate_shops, deactivate_shops, deactivate_users
from .call_rollups import call_user_snapshot_api, call_shop_snapshot_api


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def make_list_unique(input_list: list) -> list:
    """
    Remove duplicate items from a list based on their id attribute.

    :param input_list: List of items to deduplicate
    :return: List of unique items
    """
    unique_list = []
    seen_ids = set()
    for item in input_list:
        if item is not None and item.id not in seen_ids:
            unique_list.append(item)
            seen_ids.add(item.id)
    return unique_list

class ActionCounter(BaseModel):
    """Model to keep track of various action counts."""
    users_created: int = 0
    users_deactivated: int = 0
    shops_created: int = 0
    shops_deleted: int = 0
    active_users: int = 0
    active_shops: int = 0

class Batch(BaseModel):
    """Model to represent a batch of operations."""
    new_users: List[User] = Field(default_factory=list)
    del_users: List[User] = Field(default_factory=list)
    new_shops: List[Shop] = Field(default_factory=list)
    del_shops: List[Shop] = Field(default_factory=list)
    active_users: List[Shop] = Field(default_factory=list)
    active_shops: List[Shop] = Field(default_factory=list)
    om: OddsMaker = Field(default_factory=OddsMaker)
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: Optional[timedelta] = None

    def start(self):
        """Mark the start time of the batch."""
        self.start_time = datetime.now()

    def end(self):
        """Mark the end time of the batch and calculate duration."""
        self.end_time = datetime.now()
        self.duration = self.end_time - self.start_time

class BaseDataStore(BaseModel):
    """Main data store for managing users and shops."""
    active_users: Dict[uuid.UUID, User] = Field(default_factory=dict)
    active_shops: Dict[uuid.UUID, Shop] = Field(default_factory=dict)
    action_counter: ActionCounter = Field(default_factory=ActionCounter)
    all_action_counter: Dict[datetime, Dict] = Field(default_factory=dict)
    batch: Batch = Field(default_factory=Batch)
    all_batch: Dict[datetime, Batch] = Field(default_factory=dict)

    def post_batch_update(self, current_date: datetime):
        """
        Process and log the results of a batch operation.

        :param current_date: The date of the current batch
        """
        try:
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
            self._validate_counts()

            # Log batch information
            self._log_batch_info(new_users, new_shops, del_shops, del_users)

            # Update all_action_counter
            self._update_all_action_counter(current_date)

            # Calculate and log daily changes
            self._log_daily_changes(current_date)

            self.all_batch[current_date] = self.batch


            # Log additional metrics
            self._log_additional_metrics()

        except Exception as e:
            logger.error(f"Error in post_batch_update: {str(e)}")

    def _validate_counts(self):
        """Validate the counts of users and shops."""
        expected_active_users = self.action_counter.users_created - self.action_counter.users_deactivated
        expected_active_shops = self.action_counter.shops_created - self.action_counter.shops_deleted

        if self.action_counter.active_users != expected_active_users:
            logger.warning(f"Mismatch in active users count. Expected: {expected_active_users}, Actual: {self.action_counter.active_users}")

        if self.action_counter.active_shops != expected_active_shops:
            logger.warning(f"Mismatch in active shops count. Expected: {expected_active_shops}, Actual: {self.action_counter.active_shops}")

        for attr, value in self.action_counter.__dict__.items():
            if value < 0:
                logger.error(f"Negative value detected for {attr}: {value}")

    def _log_batch_info(self, new_users, new_shops, del_shops, del_users):
        """Log information about the current batch."""
        logger.info(f"Batch Generated {len(new_users)} users")
        logger.info(f"Batch Generated {len(new_shops)} shops")
        logger.info(f"Batch Deactivated {len(del_shops)} shops")
        logger.info(f"Batch Deactivated {len(del_users)} users")
        logger.info(f"Total Users created: {self.action_counter.users_created}")
        logger.info(f"Total Users deactivated: {self.action_counter.users_deactivated}")
        logger.info(f"Total Shops created: {self.action_counter.shops_created}")
        logger.info(f"Total Shops deactivated: {self.action_counter.shops_deleted}")
        logger.info(f"Active users: {self.action_counter.active_users}")
        logger.info(f"Active shops: {self.action_counter.active_shops}")
        logger.info(f"Batch processing time: {self.batch.duration}")

    def _update_all_action_counter(self, current_date):
        """Update the all_action_counter with the current batch's data."""
        self.all_action_counter[current_date] = {
            **self.action_counter.dict(),
            'processing_time': self.batch.duration.total_seconds()
        }

    def _log_daily_changes(self, current_date):
        """Log the changes since the previous batch."""
        if len(self.all_action_counter) > 1:
            previous_date = max(date for date in self.all_action_counter.keys() if date < current_date)
            previous_counter = self.all_action_counter[previous_date]
            
            logger.info("Daily changes:")
            for key in self.action_counter.__dict__.keys():
                daily_change = self.action_counter.__dict__[key] - previous_counter[key]
                logger.info(f"  {key}: {daily_change}")
            
            time_change = self.all_action_counter[current_date]['processing_time'] - previous_counter['processing_time']
            logger.info(f"  processing_time change: {time_change:.2f} seconds")

    def _log_additional_metrics(self):
        """Log additional metrics about users and shops."""
        active_user_list = list(self.active_users.values())
        shops_per_user = [len(user.shops) for user in active_user_list]
        avg_shops_per_user = sum(shops_per_user) / len(active_user_list) if active_user_list else 0

        logger.info(f" Average shops per active user: {avg_shops_per_user:.2f}")
        logger.info(f" Shop distribution:")
        for i in range(max(shops_per_user) + 1):
            count = shops_per_user.count(i)
            percentage = (count / len(active_user_list)) * 100 if active_user_list else 0
            logger.info(f"  Users with {i} shops: {count} ({percentage:.2f}%)")

    def create_batch(self):
        """Create a new batch and reset batch counters."""
        self.batch = Batch()
        self.batch.active_users = list(self.active_users.values())
        self.batch.active_shops = list(self.active_shops.values())
        self.batch.new_users = []
        self.batch.del_users = []
        self.batch.new_shops = []
        self.batch.del_shops = []
        logger.info("New batch created and counters reset")

    async def process_day(self, current_date: datetime, om = OddsMaker()):
        """
        Process a day's worth of user and shop activities.

        :param current_date: The date to process
        """
        try:
            self.create_batch()

            if om:
                self.batch.om = om

            self.batch.start()
            user_count = await self.batch.om.generate_fake_user_growth_amount(self.active_users)

            self.batch.new_users = await generate_users(user_count, current_date)
            logger.info(f"Generated {len(self.batch.new_users)} new users")

            new_shop_users = await self.batch.om.generate_fake_shop_growth(self.batch.new_users, self.batch.active_shops)
            self.batch.new_shops = await generate_shops(new_shop_users, user_count, current_date)
            logger.info(f"Generated {len(self.batch.new_shops)} new shops from new users")

            new_shop_users = await self.batch.om.generate_fake_shop_growth(self.batch.active_users, self.batch.active_shops)
            additional_shops = await generate_shops(new_shop_users, user_count, current_date)
            self.batch.new_shops += additional_shops
            logger.info(f"Generated {len(additional_shops)} additional new shops from active users")

            shop_churn_list = await self.batch.om.generate_fake_shop_churn(self.batch.active_shops)
            within_deactivated_shops = await deactivate_shops(shop_churn_list, user_count, current_date)
            logger.info(f"Deactivated {len(within_deactivated_shops)} shops")

            users_to_deactivate = await self.batch.om.generate_fake_user_churn(self.batch.active_users)
            del_users, deactivated_shops = await deactivate_users(users_to_deactivate, user_count, current_date)
            logger.info(f"Deactivated {len(del_users)} users and {len(deactivated_shops)} associated shops")

            self.batch.del_users = del_users
            self.batch.del_shops = [shop for shop in (within_deactivated_shops + deactivated_shops) if shop is not None]

            self.batch.end()
            logger.info(f"Day processing completed in {self.batch.duration}")
            
            await asyncio.gather(
                call_user_snapshot_api(current_date),
                call_shop_snapshot_api(current_date)
            )
            
            self.post_batch_update(current_date)
        except Exception as e:
            logger.error(f"Error in process_day: {str(e)}")

    def analyze_trends(self):
        """Analyze trends in the data and generate reports."""
        try:
            dates = sorted(self.all_action_counter.keys())
            if len(dates) < 2:
                logger.info("Not enough data to analyze trends")
                return

            first_date = dates[0]
            last_date = dates[-1]
            first_counter = self.all_action_counter[first_date]
            last_counter = self.all_action_counter[last_date]

            report_dir = os.path.join(os.getcwd(), "fake_data_reports")
            os.makedirs(report_dir, exist_ok=True)

            current_time = datetime.now()
            filename_base = current_time.strftime("%Y_%m_%d_%H_%M")
            txt_filename = os.path.join(report_dir, f"{filename_base}.txt")
            json_filename = os.path.join(report_dir, f"{filename_base}.json")

            report_content = []
            json_content = {"trend_analysis": {}}

            report_content.append(f"Trend analysis from {first_date} to {last_date}:")
            for key in first_counter.keys():
                self._analyze_trend(key, first_counter, last_counter, dates, report_content, json_content)

            self._calculate_processing_time_stats(report_content, json_content)

            with open(txt_filename, 'w') as f:
                f.write('\n'.join(report_content))

            with open(json_filename, 'w') as f:
                json.dump(json_content, f, indent=2)

            logger.info(f"Trend analysis report saved to {txt_filename}")
            logger.info(f"Trend analysis JSON saved to {json_filename}")

            for line in report_content:
                logger.info(line)

        except Exception as e:
            logger.error(f"Error in analyze_trends: {str(e)}")

    def _analyze_trend(self, key, first_counter, last_counter, dates, report_content, json_content):
        """Analyze trend for a specific key."""
        total_change = last_counter[key] - first_counter[key]
        avg_daily_change = total_change / (len(dates) - 1)

        if key == 'processing_time':
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
            report_content.extend([
                f"  {key}:",
                f"    Total change: {total_change}",
                f"    Average daily change: {avg_daily_change:.2f}"
            ])
            
            json_content["trend_analysis"][key] = {
                "total_change": total_change,
                "avg_daily_change": avg_daily_change
            }

    def _calculate_processing_time_stats(self, report_content, json_content):
        """Calculate and log processing time statistics."""
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

    def get_user_stats(self) -> Dict[str, float]:
        """
        Calculate and return user statistics.

        :return: Dictionary containing user statistics
        """
        try:
            active_user_list = list(self.active_users.values())
            total_users = len(active_user_list)
            total_shops = sum(len(user.shops) for user in active_user_list)
            
            avg_shops_per_user = total_shops / total_users if total_users > 0 else 0
            users_with_shops = sum(1 for user in active_user_list if user.shops)
            percent_users_with_shops = (users_with_shops / total_users) * 100 if total_users > 0 else 0

            return {
                "total_active_users": total_users,
                "total_shops": total_shops,
                "avg_shops_per_user": avg_shops_per_user,
                "percent_users_with_shops": percent_users_with_shops
            }
        except Exception as e:
            logger.error(f"Error in get_user_stats: {str(e)}")
            return {}

    def get_shop_distribution(self) -> Dict[int, int]:
        """
        Calculate the distribution of shops per user.

        :return: Dictionary with number of shops as keys and count of users as values
        """
        try:
            distribution = {}
            for user in self.active_users.values():
                shop_count = len(user.shops)
                distribution[shop_count] = distribution.get(shop_count, 0) + 1
            return distribution
        except Exception as e:
            logger.error(f"Error in get_shop_distribution: {str(e)}")
            return {}

    def log_current_state(self):
        """Log the current state of the data store."""
        try:
            user_stats = self.get_user_stats()
            shop_distribution = self.get_shop_distribution()

            logger.info("Current Data Store State:")
            logger.info(f"Total active users: {user_stats['total_active_users']}")
            logger.info(f"Total shops: {user_stats['total_shops']}")
            logger.info(f"Average shops per user: {user_stats['avg_shops_per_user']:.2f}")
            logger.info(f"Percent of users with shops: {user_stats['percent_users_with_shops']:.2f}%")
            
            logger.info("Shop distribution:")
            for shop_count, user_count in shop_distribution.items():
                logger.info(f"  Users with {shop_count} shops: {user_count}")

        except Exception as e:
            logger.error(f"Error in log_current_state: {str(e)}")

    def save_state(self, filename: str):
        """
        Save the current state of the data store to a file.

        :param filename: Name of the file to save the state
        """
        try:
            state = {
                "active_users": {str(k): v.dict() for k, v in self.active_users.items()},
                "active_shops": {str(k): v.dict() for k, v in self.active_shops.items()},
                "action_counter": self.action_counter.dict(),
                "all_action_counter": {str(k): v for k, v in self.all_action_counter.items()},
                "all_batch": {str(k): v.dict() for k, v in self.all_batch.items()}
            }
            with open(filename, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"Data store state saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving state to {filename}: {str(e)}")

    @classmethod
    def load_state(cls, filename: str):
        """
        Load the state of the data store from a file.

        :param filename: Name of the file to load the state from
        :return: Instance of BaseDataStore with loaded state
        """
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            data_store = cls()
            data_store.active_users = {uuid.UUID(k): User(**v) for k, v in state["active_users"].items()}
            data_store.active_shops = {uuid.UUID(k): Shop(**v) for k, v in state["active_shops"].items()}
            data_store.action_counter = ActionCounter(**state["action_counter"])
            data_store.all_action_counter = {datetime.fromisoformat(k): v for k, v in state["all_action_counter"].items()}
            data_store.all_batch = {datetime.fromisoformat(k): Batch(**v) for k, v in state["all_batch"].items()}
            
            logger.info(f"Data store state loaded from {filename}")
            return data_store
        except Exception as e:
            logger.error(f"Error loading state from {filename}: {str(e)}")
            return None
        
    async def process_date_range(self, start_date: datetime, end_date: datetime, om = OddsMaker()):
        current_date = start_date
        while current_date <= end_date:
            print(f"Processing date: {current_date.date()}")
            await self.process_day(current_date, om)
            current_date += timedelta(days=1)
        self.analyze_trends()
        return self.action_counter