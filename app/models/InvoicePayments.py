from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, Boolean, JSON, Enum, Float, UUID, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
from .enums import PaymentMethodType, PaymentStatus

class InvoicePayment(Base, PartitionedModel):
    """
    Represents a payment made towards an invoice for running a shop.
    Links to the user making the payment, the invoice being paid,
    and the shop the invoice is for.
    
    Indexing Strategy:
    - Primary key (id, partition_key)
    - status is indexed for filtering by payment status
    - user_id is indexed for user-based queries
    - invoice_id is indexed for invoice-based queries
    - shop_id is indexed for shop-based queries
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'invoice_payments'
    __partitiontype__ = "hourly"
    __partition_field__ = "event_time"

    # Primary Fields
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the payment"
    )
    user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the user making the payment"
    )
    invoice_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the invoice being paid"
    )
    shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the shop the invoice is for"
    )
    payment_method_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the payment method used"
    )
    
    # Payment Details
    amount = Column(
        Float, 
        nullable=False,
        comment="Amount of the payment"
    )
    status = Column(
        Enum(PaymentStatus, schema='data_playground'), 
        nullable=False, 
        default=PaymentStatus.PENDING,
        comment="Current status of the payment"
    )
    method = Column(
        Enum(PaymentMethodType, schema='data_playground'), 
        nullable=False,
        comment="Method used for payment"
    )
    is_partial_payment = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Whether this is a partial payment"
    )
    
    # Transaction Details
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
    transaction_fee = Column(
        Float, 
        nullable=True, 
        default=0.0,
        comment="Fee charged for processing payment"
    )
    
    # Timestamps
    initiated_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        comment="When the payment was initiated"
    )
    completed_time = Column(
        DateTime(timezone=True), 
        nullable=True,
        comment="When the payment was completed"
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
        comment="Notes about the payment"
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

    # Relationships
    user = relationship(
        "User",
        backref=backref("invoice_payments", lazy="dynamic"),
        foreign_keys=[user_id]
    )
    invoice = relationship(
        "Invoice",
        backref=backref("payments", lazy="dynamic"),
        foreign_keys=[invoice_id]
    )
    shop = relationship(
        "Shop",
        backref=backref("invoice_payments", lazy="dynamic"),
        foreign_keys=[shop_id]
    )
    payment_method = relationship(
        "UserPaymentMethod",
        backref=backref("invoice_payments", lazy="dynamic"),
        foreign_keys=[payment_method_id]
    )

    __table_args__ = (
        UniqueConstraint('transaction_reference', 'partition_key', name='uq_invoice_payments_transaction_ref'),
        ForeignKeyConstraint(
            ['user_id', 'partition_key'],
            ['data_playground.users.id', 'data_playground.users.partition_key'],
            name='fk_invoice_payment_user',
            comment="Foreign key relationship to the users table"
        ),
        ForeignKeyConstraint(
            ['invoice_id', 'partition_key'],
            ['data_playground.invoices.invoice_id', 'data_playground.invoices.partition_key'],
            name='fk_invoice_payment_invoice',
            comment="Foreign key relationship to the invoices table"
        ),
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['data_playground.shops.id', 'data_playground.shops.partition_key'],
            name='fk_invoice_payment_shop',
            comment="Foreign key relationship to the shops table"
        ),
        ForeignKeyConstraint(
            ['payment_method_id', 'partition_key'],
            ['data_playground.user_payment_methods.id', 'data_playground.user_payment_methods.partition_key'],
            name='fk_invoice_payment_method',
            comment="Foreign key relationship to the payment_methods table"
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores invoice payment data with hourly partitioning for efficient querying'
        }
    )

    async def process_payment(self, db):
        """Process the payment"""
        self.status = PaymentStatus.PROCESSING
        await db.commit()
        
        try:
            # Simulate payment processing
            # In real implementation, this would integrate with payment gateway
            success = True  # Replace with actual payment processing
            
            if success:
                await self.complete_payment(db)
            else:
                await self.fail_payment(db)
            
            return success
        except Exception as e:
            await self.fail_payment(db, str(e))
            return False

    async def complete_payment(self, db):
        """Mark payment as completed and create event"""
        self.status = PaymentStatus.COMPLETED
        self.completed_time = datetime.utcnow()
        await db.commit()
        
        # Create global event for successful payment
        from .global_event import GlobalEvent, EventType
        await GlobalEvent.create_user_event(
            db,
            EventType.invoice_payment_success,
            self.user_id,
            payment_id=str(self.id),
            amount=self.amount,
            invoice_id=str(self.invoice_id),
            shop_id=str(self.shop_id)
        )

    async def fail_payment(self, db, error_message=None):
        """Mark payment as failed and create event"""
        self.status = PaymentStatus.FAILED
        if error_message:
            self.notes = error_message
        await db.commit()
        
        # Create global event for failed payment
        from .global_event import GlobalEvent, EventType
        await GlobalEvent.create_user_event(
            db,
            EventType.invoice_payment_failed,
            self.user_id,
            payment_id=str(self.id),
            amount=self.amount,
            invoice_id=str(self.invoice_id),
            shop_id=str(self.shop_id),
            error=error_message
        )

    async def refund_payment(self, db, amount=None, reason=None):
        """Process a refund"""
        if self.status != PaymentStatus.COMPLETED:
            raise ValueError("Can only refund completed payments")
        
        refund_amount = amount if amount else self.amount
        if refund_amount > self.amount:
            raise ValueError("Refund amount cannot exceed payment amount")
        
        # Update status based on refund amount
        if refund_amount == self.amount:
            self.status = PaymentStatus.REFUNDED
        else:
            self.status = PaymentStatus.PARTIALLY_REFUNDED
        
        self.notes = f"Refunded: {refund_amount}. Reason: {reason}" if reason else f"Refunded: {refund_amount}"
        await db.commit()
        
        # Create global event for refund
        from .global_event import GlobalEvent, EventType
        await GlobalEvent.create_user_event(
            db,
            EventType.invoice_payment_refunded,
            self.user_id,
            payment_id=str(self.id),
            amount=refund_amount,
            invoice_id=str(self.invoice_id),
            shop_id=str(self.shop_id),
            reason=reason
        )
