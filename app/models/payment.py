from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, JSON, Enum, Float, UUID, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime
import enum
from .invoice import FakeUserInvoice

class PaymentStatus(enum.Enum):
    """Possible states for a payment"""
    PENDING = "pending"  # Payment initiated
    PROCESSING = "processing"  # Payment being processed
    COMPLETED = "completed"  # Payment successful
    FAILED = "failed"  # Payment failed
    REFUNDED = "refunded"  # Payment fully refunded
    CANCELLED = "cancelled"  # Payment cancelled
    PARTIALLY_REFUNDED = "partially_refunded"  # Payment partially refunded

class PaymentMethod(enum.Enum):
    """Types of payment methods accepted"""
    CREDIT_CARD = "credit_card"  # Credit card payment
    DEBIT_CARD = "debit_card"  # Debit card payment
    BANK_TRANSFER = "bank_transfer"  # Direct bank transfer
    DIGITAL_WALLET = "digital_wallet"  # Digital wallet (PayPal, etc.)
    CRYPTO = "cryptocurrency"  # Cryptocurrency payment
    CASH = "cash"  # Cash payment
    CHECK = "check"  # Check payment
    OTHER = "other"  # Other payment types

class FakeUserPayment(Base, PartitionedModel):
    """
    Represents a payment made by a user. Payments are linked to invoices
    and can be used across multiple orders. Tracks payment status,
    refunds, and transaction details.
    """
    __tablename__ = 'fake_user_payments'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    # Primary Fields
    payment_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the payment"
    )
    fake_user_invoice_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the invoice being paid"
    )
    
    # Payment Details
    payment_amount = Column(
        Float, 
        nullable=False,
        comment="Amount of the payment"
    )
    payment_status = Column(
        Enum(PaymentStatus), 
        nullable=False, 
        default=PaymentStatus.PENDING,
        comment="Current status of the payment"
    )
    payment_method = Column(
        Enum(PaymentMethod), 
        nullable=False,
        comment="Method used for payment"
    )
    
    # Transaction Details
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
    payment_initiated_time = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=datetime.utcnow,
        comment="When the payment was initiated"
    )
    payment_completed_time = Column(
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
    payment_notes = Column(
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
    # Order payments linked to this payment
    order_payments = relationship(
        "FakeUserShopOrderPayment",
        backref=backref("payment", lazy="joined"),
        foreign_keys="FakeUserShopOrderPayment.payment_id",
        lazy="dynamic"
    )

    # Invoice this payment is for
    invoice = relationship(
        "FakeUserInvoice",
        backref=backref("payments", lazy="dynamic"),
        foreign_keys=[fake_user_invoice_id]
    )

    __table_args__ = (
        # Unique constraint for transaction reference must include partition key
        UniqueConstraint('transaction_reference', 'partition_key', name='uq_fake_user_payments_transaction_ref'),
        
        # Foreign key constraint with partition key
        ForeignKeyConstraint(
            ['fake_user_invoice_id', 'partition_key'],
            ['data_playground.fake_user_invoices.invoice_id', 'data_playground.fake_user_invoices.partition_key'],
            name='fk_fake_user_payment_invoice',
            comment="Foreign key relationship to the fake_user_invoices table"
        ),
        
        # Partitioning configuration
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores payment data for fake users'
        }
    )

    # Helper Methods for Payment Processing
    async def process_payment(self, db):
        """Process the payment"""
        self.payment_status = PaymentStatus.PROCESSING
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
        """Mark payment as completed"""
        self.payment_status = PaymentStatus.COMPLETED
        self.payment_completed_time = datetime.utcnow()
        await db.commit()
        
        # Create global event for successful payment
        from .global_event import GlobalEvent, EventType
        await GlobalEvent.create_user_event(
            db,
            EventType.fake_user_payment_success,
            self.invoice.fake_user_id,
            payment_id=str(self.payment_id),
            amount=self.payment_amount
        )

    async def fail_payment(self, db, error_message=None):
        """Mark payment as failed"""
        self.payment_status = PaymentStatus.FAILED
        if error_message:
            self.payment_notes = error_message
        await db.commit()
        
        # Create global event for failed payment
        from .global_event import GlobalEvent, EventType
        await GlobalEvent.create_user_event(
            db,
            EventType.fake_user_payment_failed,
            self.invoice.fake_user_id,
            payment_id=str(self.payment_id),
            amount=self.payment_amount,
            error=error_message
        )

    async def refund_payment(self, db, amount=None, reason=None):
        """Process a refund"""
        if self.payment_status != PaymentStatus.COMPLETED:
            raise ValueError("Can only refund completed payments")
        
        refund_amount = amount if amount else self.payment_amount
        if refund_amount > self.payment_amount:
            raise ValueError("Refund amount cannot exceed payment amount")
        
        # Update status based on refund amount
        if refund_amount == self.payment_amount:
            self.payment_status = PaymentStatus.REFUNDED
        else:
            self.payment_status = PaymentStatus.PARTIALLY_REFUNDED
        
        self.payment_notes = f"Refunded: {refund_amount}. Reason: {reason}" if reason else f"Refunded: {refund_amount}"
        await db.commit()

    # Helper Methods for Analysis
    @classmethod
    async def get_payment_stats(cls, db, user_id=None, start_time=None, end_time=None):
        """Get payment statistics"""
        query = db.query(cls)
        if user_id:
            query = query.join(FakeUserInvoice).filter(FakeUserInvoice.fake_user_id == user_id)
        if start_time:
            query = query.filter(cls.event_time >= start_time)
        if end_time:
            query = query.filter(cls.event_time <= end_time)
        
        payments = await query.all()
        return {
            'total_payments': len(payments),
            'total_amount': sum(p.payment_amount for p in payments),
            'successful_payments': len([p for p in payments if p.payment_status == PaymentStatus.COMPLETED]),
            'failed_payments': len([p for p in payments if p.payment_status == PaymentStatus.FAILED]),
            'refunded_payments': len([p for p in payments if p.payment_status in (PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED)]),
            'average_amount': sum(p.payment_amount for p in payments) / len(payments) if payments else 0,
            'payment_methods': {
                method: len([p for p in payments if p.payment_method == method])
                for method in PaymentMethod
            }
        }
