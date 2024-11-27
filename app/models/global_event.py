from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, JSON, Enum, UUID
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
import enum
from sqlalchemy.ext.hybrid import hybrid_property
from app.schemas import GlobalEventResponse

class EventType(enum.Enum):
    # User Account Events
    fake_user_account_creation = "fake_user_account_creation"
    fake_user_delete_account = "fake_user_delete_account"
    fake_user_deactivate_account = "fake_user_deactivate_account"
    fake_user_reactivate_account = "fake_user_reactivate_account"
    fake_user_login = "fake_user_login"
    fake_user_logout = "fake_user_logout"
    fake_user_profile_update = "fake_user_profile_update"
    fake_user_password_change = "fake_user_password_change"
    fake_user_email_change = "fake_user_email_change"
    
    # Shop Events
    fake_user_shop_create = "fake_user_shop_create"
    fake_user_shop_delete = "fake_user_shop_delete"
    fake_user_shop_update = "fake_user_shop_update"
    fake_user_shop_deactivate = "fake_user_shop_deactivate"
    fake_user_shop_reactivate = "fake_user_shop_reactivate"
    fake_user_shop_settings_update = "fake_user_shop_settings_update"
    
    # Product Events
    fake_user_product_create = "fake_user_product_create"
    fake_user_product_update = "fake_user_product_update"
    fake_user_product_delete = "fake_user_product_delete"
    fake_user_product_price_change = "fake_user_product_price_change"
    fake_user_product_status_change = "fake_user_product_status_change"
    fake_user_product_category_change = "fake_user_product_category_change"
    
    # Order Events
    fake_user_order_placed = "fake_user_order_placed"
    fake_user_order_updated = "fake_user_order_updated"
    fake_user_order_cancelled = "fake_user_order_cancelled"
    fake_user_order_processing = "fake_user_order_processing"
    fake_user_order_shipped = "fake_user_order_shipped"
    fake_user_order_delivered = "fake_user_order_delivered"
    fake_user_order_returned = "fake_user_order_returned"
    fake_user_order_refunded = "fake_user_order_refunded"
    
    # Payment Events
    fake_user_payment_initiated = "fake_user_payment_initiated"
    fake_user_payment_processing = "fake_user_payment_processing"
    fake_user_payment_success = "fake_user_payment_success"
    fake_user_payment_failed = "fake_user_payment_failed"
    fake_user_payment_refunded = "fake_user_payment_refunded"
    fake_user_payment_partially_refunded = "fake_user_payment_partially_refunded"
    fake_user_payment_disputed = "fake_user_payment_disputed"
    fake_user_payment_dispute_resolved = "fake_user_payment_dispute_resolved"
    
    # Payment Method Events
    fake_user_payment_method_added = "fake_user_payment_method_added"
    fake_user_payment_method_updated = "fake_user_payment_method_updated"
    fake_user_payment_method_removed = "fake_user_payment_method_removed"
    fake_user_payment_method_expired = "fake_user_payment_method_expired"
    fake_user_payment_method_default_changed = "fake_user_payment_method_default_changed"
    
    # Review Events
    fake_user_review_posted = "fake_user_review_posted"
    fake_user_review_updated = "fake_user_review_updated"
    fake_user_review_deleted = "fake_user_review_deleted"
    fake_user_review_reported = "fake_user_review_reported"
    fake_user_review_status_changed = "fake_user_review_status_changed"
    fake_user_review_vote_added = "fake_user_review_vote_added"
    fake_user_review_vote_removed = "fake_user_review_vote_removed"
    
    # Promotion Events
    fake_user_promotion_created = "fake_user_promotion_created"
    fake_user_promotion_updated = "fake_user_promotion_updated"
    fake_user_promotion_activated = "fake_user_promotion_activated"
    fake_user_promotion_deactivated = "fake_user_promotion_deactivated"
    fake_user_promotion_used = "fake_user_promotion_used"
    fake_user_promotion_expired = "fake_user_promotion_expired"
    fake_user_promotion_limit_reached = "fake_user_promotion_limit_reached"
    
    # Inventory Events
    fake_user_inventory_updated = "fake_user_inventory_updated"
    fake_user_inventory_low = "fake_user_inventory_low"
    fake_user_inventory_out = "fake_user_inventory_out"
    fake_user_inventory_restocked = "fake_user_inventory_restocked"
    fake_user_inventory_adjusted = "fake_user_inventory_adjusted"
    fake_user_inventory_audit = "fake_user_inventory_audit"
    
    # Invoice Events
    fake_user_invoice_created = "fake_user_invoice_created"
    fake_user_invoice_updated = "fake_user_invoice_updated"
    fake_user_invoice_paid = "fake_user_invoice_paid"
    fake_user_invoice_cancelled = "fake_user_invoice_cancelled"
    fake_user_invoice_overdue = "fake_user_invoice_overdue"
    fake_user_invoice_reminder_sent = "fake_user_invoice_reminder_sent"
    
    # Metric Events
    fake_user_metrics_updated = "fake_user_metrics_updated"
    fake_user_shop_metrics_updated = "fake_user_shop_metrics_updated"
    fake_user_product_metrics_updated = "fake_user_product_metrics_updated"
    fake_user_metrics_rollup_started = "fake_user_metrics_rollup_started"
    fake_user_metrics_rollup_completed = "fake_user_metrics_rollup_completed"
    fake_user_metrics_rollup_failed = "fake_user_metrics_rollup_failed"
    
    # System Events
    fake_user_system_startup = "fake_user_system_startup"
    fake_user_system_shutdown = "fake_user_system_shutdown"
    fake_user_system_maintenance_started = "fake_user_system_maintenance_started"
    fake_user_system_maintenance_completed = "fake_user_system_maintenance_completed"
    fake_user_system_backup_started = "fake_user_system_backup_started"
    fake_user_system_backup_completed = "fake_user_system_backup_completed"
    fake_user_system_restore_started = "fake_user_system_restore_started"
    fake_user_system_restore_completed = "fake_user_system_restore_completed"
    
    # Data Integrity Events
    fake_user_data_validation_started = "fake_user_data_validation_started"
    fake_user_data_validation_completed = "fake_user_data_validation_completed"
    fake_user_data_corruption_detected = "fake_user_data_corruption_detected"
    fake_user_data_repair_started = "fake_user_data_repair_started"
    fake_user_data_repair_completed = "fake_user_data_repair_completed"
    
    # API and Rate Limiting Events
    fake_user_api_rate_limit_warning = "fake_user_api_rate_limit_warning"
    fake_user_api_rate_limit_exceeded = "fake_user_api_rate_limit_exceeded"
    fake_user_api_throttling_applied = "fake_user_api_throttling_applied"
    fake_user_api_key_created = "fake_user_api_key_created"
    fake_user_api_key_revoked = "fake_user_api_key_revoked"
    
    # Security Events
    fake_user_security_suspicious_activity = "fake_user_security_suspicious_activity"
    fake_user_security_login_attempt_failed = "fake_user_security_login_attempt_failed"
    fake_user_security_password_reset = "fake_user_security_password_reset"
    fake_user_security_2fa_enabled = "fake_user_security_2fa_enabled"
    fake_user_security_2fa_disabled = "fake_user_security_2fa_disabled"
    
    # Error Events
    fake_user_error_occurred = "fake_user_error_occurred"
    fake_user_shop_error_occurred = "fake_user_shop_error_occurred"
    fake_user_payment_error_occurred = "fake_user_payment_error_occurred"
    fake_user_system_error_occurred = "fake_user_system_error_occurred"

class GlobalEvent(Base, PartitionedModel):
    """
    Tracks all significant events in the system, providing a comprehensive audit trail
    and enabling system-wide monitoring and analysis.
    """
    __tablename__ = "global_events"
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    # Primary Fields
    event_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the event"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False,
        comment="Timestamp when the event occurred (with timezone)"
    )
    event_type = Column(
        Enum(EventType), 
        nullable=False,
        comment="Type of event that occurred (e.g., user creation, payment, etc.)"
    )
    event_metadata = Column(
        JSON, 
        nullable=True,
        comment="Additional event-specific data stored as JSON"
    )
    caller_entity_id = Column(UUID(as_uuid=True), 
                              nullable=True, 
                              comment="ID of the entity that triggered the event"
                              )
    fake_user_id = Column(
        UUID(as_uuid=True), 
        nullable=True,
        comment="ID of the user associated with this event (if applicable)"
    )
    
    # Additional Data
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional arbitrary data related to the event"
    )
    
    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False, 
        index=True,
        comment="Key used for time-based table partitioning"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['fake_user_id'], ['data_playground.fake_users.id'],
            name='fk_global_event_fake_user',
            comment="Foreign key relationship to the fake_users table"
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground'
        }
    )

    @hybrid_property
    def response(self):
        return GlobalEventResponse(
            event_id=str(self.event_id),
            event_time=self.event_time,
            event_type=self.event_type.value,
            event_metadata=self.event_metadata
        )

    # Helper Methods for Event Creation
    @classmethod
    async def create_user_event(cls, db, event_type, user_id, **metadata):
        """Create a user-related event"""
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_shop_event(cls, db, event_type, shop_id, user_id=None, **metadata):
        """Create a shop-related event"""
        metadata['shop_id'] = str(shop_id)
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_order_event(cls, db, event_type, order_id, user_id, **metadata):
        """Create an order-related event"""
        metadata['order_id'] = str(order_id)
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_product_event(cls, db, event_type, product_id, shop_id, user_id=None, **metadata):
        """Create a product-related event"""
        metadata.update({
            'product_id': str(product_id),
            'shop_id': str(shop_id)
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_payment_event(cls, db, event_type, payment_id, user_id, **metadata):
        """Create a payment-related event"""
        metadata['payment_id'] = str(payment_id)
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_review_event(cls, db, event_type, review_id, user_id, **metadata):
        """Create a review-related event"""
        metadata['review_id'] = str(review_id)
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_promotion_event(cls, db, event_type, promotion_id, shop_id, user_id=None, **metadata):
        """Create a promotion-related event"""
        metadata.update({
            'promotion_id': str(promotion_id),
            'shop_id': str(shop_id)
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_error_event(cls, db, event_type, error_message, user_id=None, **metadata):
        """Create an error event"""
        metadata['error_message'] = error_message
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    # Helper Methods for Event Analysis
    @classmethod
    async def get_user_events(cls, db, user_id, event_types=None, start_time=None, end_time=None):
        """Get events for a specific user"""
        query = db.query(cls).filter(cls.fake_user_id == user_id)
        if event_types:
            query = query.filter(cls.event_type.in_(event_types))
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        return await query.order_by(cls.event_time.desc()).all()

    @classmethod
    async def get_shop_events(cls, db, shop_id, event_types=None, start_time=None, end_time=None):
        """Get events for a specific shop"""
        query = db.query(cls).filter(
            cls.event_metadata.contains({'shop_id': str(shop_id)})
        )
        if event_types:
            query = query.filter(cls.event_type.in_(event_types))
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        return await query.order_by(cls.event_time.desc()).all()

    @classmethod
    async def get_product_events(cls, db, product_id, event_types=None, start_time=None, end_time=None):
        """Get events for a specific product"""
        query = db.query(cls).filter(
            cls.event_metadata.contains({'product_id': str(product_id)})
        )
        if event_types:
            query = query.filter(cls.event_type.in_(event_types))
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        return await query.order_by(cls.event_time.desc()).all()

    @classmethod
    async def get_error_events(cls, db, error_types=None, start_time=None, end_time=None):
        """Get error events"""
        query = db.query(cls).filter(
            cls.event_type.in_([
                EventType.fake_user_error_occurred,
                EventType.fake_user_shop_error_occurred,
                EventType.fake_user_payment_error_occurred,
                EventType.fake_user_system_error_occurred
            ])
        )
        if error_types:
            query = query.filter(cls.event_type.in_(error_types))
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        return await query.order_by(cls.event_time.desc()).all()

    @classmethod
    async def get_event_stats(cls, db, event_types=None, start_time=None, end_time=None):
        """Get statistics for events"""
        query = db.query(cls)
        if event_types:
            query = query.filter(cls.event_type.in_(event_types))
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        
        events = await query.all()
        return {
            'total_events': len(events),
            'events_by_type': {
                event_type: len([e for e in events if e.event_type == event_type])
                for event_type in EventType
            },
            'unique_users': len(set(event.fake_user_id for event in events if event.fake_user_id))
        }

    # Helper Methods for Event Creation
    @classmethod
    async def create_system_event(cls, db, event_type, **metadata):
        """Create a system-related event"""
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_maintenance_event(cls, db, event_type, maintenance_type, **metadata):
        """Create a maintenance-related event"""
        metadata.update({
            'maintenance_type': maintenance_type,
            'start_time': datetime.utcnow().isoformat() if 'started' in event_type.value else None,
            'end_time': datetime.utcnow().isoformat() if 'completed' in event_type.value else None
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    # Helper Methods for Data Integrity Events
    @classmethod
    async def create_data_validation_event(cls, db, event_type, validation_type, results=None, **metadata):
        """Create a data validation event"""
        metadata.update({
            'validation_type': validation_type,
            'validation_results': results,
            'timestamp': datetime.utcnow().isoformat()
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_data_corruption_event(cls, db, corruption_details, affected_tables=None, **metadata):
        """Create a data corruption event"""
        metadata.update({
            'corruption_details': corruption_details,
            'affected_tables': affected_tables,
            'detected_time': datetime.utcnow().isoformat()
        })
        event = await cls.create_with_partition(
            db,
            event_type=EventType.fake_user_data_corruption_detected,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    # Helper Methods for API and Rate Limiting Events
    @classmethod
    async def create_api_event(cls, db, event_type, api_key=None, endpoint=None, user_id=None, **metadata):
        """Create an API-related event"""
        metadata.update({
            'api_key': api_key,
            'endpoint': endpoint,
            'timestamp': datetime.utcnow().isoformat()
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    @classmethod
    async def create_rate_limit_event(cls, db, event_type, user_id, endpoint, current_rate=None, limit=None, **metadata):
        """Create a rate limit event"""
        metadata.update({
            'endpoint': endpoint,
            'current_rate': current_rate,
            'rate_limit': limit,
            'timestamp': datetime.utcnow().isoformat()
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    # Helper Methods for Security Events
    @classmethod
    async def create_security_event(cls, db, event_type, user_id, ip_address=None, user_agent=None, **metadata):
        """Create a security-related event"""
        metadata.update({
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.utcnow().isoformat()
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            fake_user_id=user_id,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    # Helper Methods for Metric Events
    @classmethod
    async def create_metric_rollup_event(cls, db, event_type, metric_type, start_time=None, end_time=None, **metadata):
        """Create a metric rollup event"""
        metadata.update({
            'metric_type': metric_type,
            'rollup_start_time': start_time.isoformat() if start_time else None,
            'rollup_end_time': end_time.isoformat() if end_time else None,
            'timestamp': datetime.utcnow().isoformat()
        })
        event = await cls.create_with_partition(
            db,
            event_type=event_type,
            event_time=datetime.utcnow(),
            event_metadata=metadata
        )
        return event

    # Additional Analysis Methods
    @classmethod
    async def get_system_health_events(cls, db, start_time=None, end_time=None):
        """Get system health-related events"""
        system_event_types = [
            EventType.fake_user_system_startup,
            EventType.fake_user_system_shutdown,
            EventType.fake_user_system_maintenance_started,
            EventType.fake_user_system_maintenance_completed,
            EventType.fake_user_data_corruption_detected,
            EventType.fake_user_system_error_occurred
        ]
        return await cls.get_event_stats(db, event_types=system_event_types, start_time=start_time, end_time=end_time)

    @classmethod
    async def get_security_events(cls, db, user_id=None, start_time=None, end_time=None):
        """Get security-related events"""
        security_event_types = [
            EventType.fake_user_security_suspicious_activity,
            EventType.fake_user_security_login_attempt_failed,
            EventType.fake_user_security_password_reset,
            EventType.fake_user_security_2fa_enabled,
            EventType.fake_user_security_2fa_disabled
        ]
        query = db.query(cls).filter(cls.event_type.in_(security_event_types))
        if user_id:
            query = query.filter(cls.fake_user_id == user_id)
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        return await query.order_by(cls.event_time.desc()).all()

    @classmethod
    async def get_metric_rollup_status(cls, db, metric_type=None, start_time=None, end_time=None):
        """Get metric rollup status"""
        metric_event_types = [
            EventType.fake_user_metrics_rollup_started,
            EventType.fake_user_metrics_rollup_completed,
            EventType.fake_user_metrics_rollup_failed
        ]
        query = db.query(cls).filter(cls.event_type.in_(metric_event_types))
        if metric_type:
            query = query.filter(cls.event_metadata.contains({'metric_type': metric_type}))
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        
        events = await query.order_by(cls.event_time.desc()).all()
        return {
            'total_rollups': len(events),
            'successful_rollups': len([e for e in events if e.event_type == EventType.fake_user_metrics_rollup_completed]),
            'failed_rollups': len([e for e in events if e.event_type == EventType.fake_user_metrics_rollup_failed]),
            'in_progress_rollups': len([e for e in events if e.event_type == EventType.fake_user_metrics_rollup_started])
        }
