from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, Float, UUID, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
import enum

class PaymentMethodType(enum.Enum):
    """Types of payment methods that can be stored"""
    CREDIT_CARD = "credit_card"  # Credit cards
    DEBIT_CARD = "debit_card"  # Debit cards
    BANK_ACCOUNT = "bank_account"  # Direct bank account
    DIGITAL_WALLET = "digital_wallet"  # Digital wallets (PayPal, etc.)
    CRYPTO_WALLET = "crypto_wallet"  # Cryptocurrency wallets

class PaymentMethodStatus(enum.Enum):
    """Possible states for a payment method"""
    ACTIVE = "active"  # Available for use
    EXPIRED = "expired"  # Card/account expired
    SUSPENDED = "suspended"  # Temporarily unavailable
    DELETED = "deleted"  # Removed by user

class FakeUserPaymentMethod(Base, PartitionedModel):
    """
    Represents a payment method saved by a user. This could be a credit card,
    bank account, or other payment type. Sensitive data is tokenized for security.
    """
    __tablename__ = 'fake_user_payment_methods'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the payment method"
    )
    fake_user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the user who owns this payment method"
    )
    
    # Payment Method Details
    method_type = Column(
        Enum(PaymentMethodType), 
        nullable=False,
        comment="Type of payment method"
    )
    status = Column(
        Enum(PaymentMethodStatus), 
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

    __table_args__ = (
        ForeignKeyConstraint(
            ['fake_user_id', 'partition_key'],
            ['data_playground.fake_users.id', 'data_playground.fake_users.partition_key'],
            name='fk_fake_user_payment_method_user',
            comment="Foreign key relationship to the fake_users table"
        ),
        UniqueConstraint('token', 'partition_key', name='uq_fake_user_payment_methods_token'),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores payment method data for fake users'
        }
    )

class FakeUserShopOrderPayment(Base, PartitionedModel):
    """
    Records a payment made on an order using a specific payment method.
    Tracks authorization details and handles partial payments.
    """
    __tablename__ = 'fake_user_shop_order_payments'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the order payment"
    )
    order_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the order being paid for"
    )
    payment_method_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the payment method used"
    )
    payment_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the payment record"
    )
    
    # Payment Details
    amount = Column(
        Float, 
        nullable=False,
        comment="Amount of this payment"
    )
    is_partial_payment = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Whether this is a partial payment"
    )
    
    # Authorization Details
    authorization_code = Column(
        String(100), 
        nullable=True,
        comment="Payment authorization code"
    )
    transaction_reference = Column(
        String(100), 
        nullable=True,
        comment="External transaction reference"
    )
    
    # Timestamps
    created_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        comment="When the payment was made"
    )
    event_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        comment="Timestamp used for partitioning"
    )
    
    # Additional Data
    notes = Column(
        String(1000), 
        nullable=True,
        comment="Payment notes"
    )
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional payment data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['order_id', 'partition_key'],
            ['data_playground.fake_user_shop_orders.id', 'data_playground.fake_user_shop_orders.partition_key'],
            name='fk_fake_user_shop_order_payment_order',
            comment="Foreign key relationship to the fake_user_shop_orders table"
        ),
        ForeignKeyConstraint(
            ['payment_method_id', 'partition_key'],
            ['data_playground.fake_user_payment_methods.id', 'data_playground.fake_user_payment_methods.partition_key'],
            name='fk_fake_user_shop_order_payment_method',
            comment="Foreign key relationship to the fake_user_payment_methods table"
        ),
        ForeignKeyConstraint(
            ['payment_id', 'partition_key'],
            ['data_playground.fake_user_payments.payment_id', 'data_playground.fake_user_payments.partition_key'],
            name='fk_fake_user_shop_order_payment_payment',
            comment="Foreign key relationship to the fake_user_payments table"
        ),
        UniqueConstraint('transaction_reference', 'partition_key', name='uq_fake_user_shop_order_payments_transaction_reference'),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores order payment data for fake user shops'
        }
    )
