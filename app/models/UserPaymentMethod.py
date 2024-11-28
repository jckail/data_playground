from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, UUID, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
from .enums import PaymentMethodType, PaymentMethodStatus

class UserPaymentMethod(Base, PartitionedModel):
    """
    Represents a payment method saved by a user. This could be a credit card,
    bank account, or other payment type. Sensitive data is tokenized for security.
    
    Indexing Strategy:
    - Primary key (id, partition_key)
    - token is indexed for unique constraint
    - user_id is indexed for user-based queries
    - method_type is indexed for filtering by payment type
    - status is indexed for filtering active/inactive methods
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'user_payment_methods'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the payment method"
    )
    user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the user who owns this payment method"
    )
    
    # Payment Method Details
    method_type = Column(
        Enum(PaymentMethodType, schema='data_playground'), 
        nullable=False,
        comment="Type of payment method"
    )
    status = Column(
        Enum(PaymentMethodStatus, schema='data_playground'), 
        nullable=False, 
        default=PaymentMethodStatus.ACTIVE,
        comment="Current status of the payment method"
    )
    
    # Tokenized/Masked Information
    token = Column(
        String(255), 
        nullable=False,
        comment="Tokenized payment method (for security)"
    )
    last_four = Column(
        String(4), 
        nullable=True,
        comment="Last 4 digits of card/account"
    )
    expiry_month = Column(
        String(2), 
        nullable=True,
        comment="Card expiration month (MM)"
    )
    expiry_year = Column(
        String(4), 
        nullable=True,
        comment="Card expiration year (YYYY)"
    )
    card_brand = Column(
        String(50), 
        nullable=True,
        comment="Card brand (Visa, Mastercard, etc.)"
    )
    bank_name = Column(
        String(255), 
        nullable=True,
        comment="Name of the bank (for bank accounts)"
    )
    
    # User-facing Details
    nickname = Column(
        String(100), 
        nullable=True,
        comment="User-defined name for this payment method"
    )
    is_default = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Whether this is the user's default payment method"
    )
    
    # Billing Address
    billing_address_line1 = Column(
        String(255), 
        nullable=True,
        comment="Primary billing address line"
    )
    billing_address_line2 = Column(
        String(255), 
        nullable=True,
        comment="Secondary billing address line"
    )
    billing_city = Column(
        String(100), 
        nullable=True,
        comment="Billing address city"
    )
    billing_state = Column(
        String(100), 
        nullable=True,
        comment="Billing address state/province"
    )
    billing_postal_code = Column(
        String(20), 
        nullable=True,
        comment="Billing address postal/ZIP code"
    )
    billing_country = Column(
        String(100), 
        nullable=True,
        comment="Billing address country"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        comment="When the payment method was added"
    )
    updated_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        comment="When the payment method was last updated"
    )
    last_used_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="When the payment method was last used"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional payment method data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    # Relationships
    user = relationship(
        "User",
        backref=backref("payment_methods", lazy="dynamic"),
        foreign_keys=[user_id]
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['user_id', 'partition_key'],
            ['data_playground.users.id', 'data_playground.users.partition_key'],
            name='fk_user_payment_method_user',
            comment="Foreign key relationship to the users table"
        ),
        UniqueConstraint('token', 'partition_key', name='uq_user_payment_methods_token'),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores user payment method data with hourly partitioning for efficient querying'
        }
    )
