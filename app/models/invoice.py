from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, JSON, Enum, Float, Integer, UUID, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime, timedelta
import enum

class InvoiceStatus(enum.Enum):
    """Possible states for an invoice"""
    DRAFT = "draft"  # Being prepared
    PENDING = "pending"  # Sent to customer
    PAID = "paid"  # Fully paid
    OVERDUE = "overdue"  # Past due date
    CANCELLED = "cancelled"  # Cancelled before payment
    REFUNDED = "refunded"  # Fully refunded
    PARTIALLY_PAID = "partially_paid"  # Partially paid

class PaymentTerms(enum.Enum):
    """Available payment terms"""
    IMMEDIATE = "immediate"  # Due immediately
    NET_15 = "net_15"  # Due in 15 days
    NET_30 = "net_30"  # Due in 30 days
    NET_45 = "net_45"  # Due in 45 days
    NET_60 = "net_60"  # Due in 60 days
    CUSTOM = "custom"  # Custom payment terms

class FakeUserInvoice(Base, PartitionedModel):
    """
    Represents an invoice issued to a user. Invoices track amounts due,
    payment terms, and payment status. They can be linked to multiple
    payments and can be used across multiple orders.
    """
    __tablename__ = 'fake_user_invoices'
    __partitiontype__ = "daily"
    __partition_field__ = "event_time"

    # Primary Fields
    invoice_id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique identifier for the invoice"
    )
    invoice_number = Column(
        String(50), 
        nullable=False,
        comment="Human-readable invoice reference number"
    )
    fake_user_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the user being invoiced"
    )
    shop_id = Column(
        UUID(as_uuid=True), 
        nullable=False,
        comment="ID of the shop issuing the invoice"
    )
    
    # Financial Details
    invoice_amount = Column(
        Float, 
        nullable=False,
        comment="Base amount before tax and discounts"
    )
    tax_amount = Column(
        Float, 
        nullable=True, 
        default=0.0,
        comment="Tax amount"
    )
    discount_amount = Column(
        Float, 
        nullable=True, 
        default=0.0,
        comment="Discount amount"
    )
    total_amount = Column(
        Float, 
        nullable=False,
        comment="Final amount including tax and discounts"
    )
    
    # Status and Terms
    status = Column(
        Enum(InvoiceStatus), 
        nullable=False, 
        default=InvoiceStatus.DRAFT,
        comment="Current status of the invoice"
    )
    payment_terms = Column(
        Enum(PaymentTerms), 
        nullable=False,
        comment="Payment terms for this invoice"
    )
    payment_term_days = Column(
        Integer, 
        nullable=True,
        comment="Number of days for custom payment terms"
    )
    
    # Timestamps
    issue_date = Column(
        DateTime(timezone=True), 
        nullable=False,
        comment="When the invoice was issued"
    )
    due_date = Column(
        DateTime(timezone=True), 
        nullable=False,
        comment="When payment is due"
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
        comment="Invoice notes"
    )
    extra_data = Column(
        JSON, 
        nullable=True, 
        default={},
        comment="Additional invoice data stored as JSON"
    )

    # Partition key for time-based partitioning
    partition_key = Column(
        String, 
        nullable=False,
        primary_key=True,
        comment="Key used for time-based table partitioning"
    )

    # Relationships
    # Payments made against this invoice
    payments = relationship(
        "FakeUserPayment",
        backref=backref("invoice", lazy="joined"),
        foreign_keys="FakeUserPayment.fake_user_invoice_id",
        lazy="dynamic"
    )

    __table_args__ = (
        # Unique constraint for invoice number must include partition key
        UniqueConstraint('invoice_number', 'partition_key', name='uq_fake_user_invoices_number'),
        
        # Foreign key constraints must include partition key
        ForeignKeyConstraint(
            ['fake_user_id', 'partition_key'],
            ['data_playground.fake_users.id', 'data_playground.fake_users.partition_key'],
            name='fk_fake_user_invoice_user',
            comment="Foreign key relationship to the fake_users table"
        ),
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['data_playground.fake_user_shops.id', 'data_playground.fake_user_shops.partition_key'],
            name='fk_fake_user_invoice_shop',
            comment="Foreign key relationship to the fake_user_shops table"
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores invoice data for fake users'
        }
    )

    # Helper Methods for Invoice Creation
    @classmethod
    async def generate_invoice_number(cls, db):
        """Generate a unique invoice number"""
        prefix = "INV"
        date_str = datetime.utcnow().strftime("%Y%m")
        
        # Get the latest invoice number for the current month
        latest_invoice = await db.query(cls).filter(
            cls.invoice_number.like(f"{prefix}{date_str}%")
        ).order_by(cls.invoice_number.desc()).first()
        
        if latest_invoice:
            sequence = int(latest_invoice.invoice_number[-4:]) + 1
        else:
            sequence = 1
        
        return f"{prefix}{date_str}{sequence:04d}"

    @classmethod
    async def create_invoice(cls, db, user_id, shop_id, amount, payment_terms, **invoice_data):
        """Create a new invoice"""
        invoice_number = await cls.generate_invoice_number(db)
        
        # Calculate due date based on payment terms
        issue_date = datetime.utcnow()
        if payment_terms == PaymentTerms.IMMEDIATE:
            due_date = issue_date
        else:
            term_days = {
                PaymentTerms.NET_15: 15,
                PaymentTerms.NET_30: 30,
                PaymentTerms.NET_45: 45,
                PaymentTerms.NET_60: 60,
            }.get(payment_terms, invoice_data.get('payment_term_days', 0))
            due_date = issue_date + timedelta(days=term_days)
        
        invoice = await cls.create_with_partition(
            db,
            invoice_number=invoice_number,
            fake_user_id=user_id,
            shop_id=shop_id,
            invoice_amount=amount,
            total_amount=amount,  # Will be updated with tax and discounts
            payment_terms=payment_terms,
            issue_date=issue_date,
            due_date=due_date,
            **invoice_data
        )
        
        return invoice

    # Helper Methods for Payment Processing
    async def record_payment(self, db, amount, payment_method, **payment_data):
        """Record a payment for this invoice"""
        from .payment import FakeUserPayment, PaymentStatus
        
        payment = await FakeUserPayment.create_with_partition(
            db,
            fake_user_invoice_id=self.invoice_id,
            payment_amount=amount,
            payment_method=payment_method,
            payment_status=PaymentStatus.PENDING,
            **payment_data
        )
        
        # Update invoice status
        total_paid = sum(p.payment_amount for p in await self.payments.filter_by(
            payment_status=PaymentStatus.COMPLETED
        ).all())
        
        if total_paid + amount >= self.total_amount:
            self.status = InvoiceStatus.PAID
        elif total_paid + amount > 0:
            self.status = InvoiceStatus.PARTIALLY_PAID
        
        await db.commit()
        return payment

    # Helper Methods for Status Management
    async def update_status(self, db):
        """Update invoice status based on payments and due date"""
        from .payment import PaymentStatus
        
        if self.status in [InvoiceStatus.CANCELLED, InvoiceStatus.REFUNDED]:
            return
        
        total_paid = sum(p.payment_amount for p in await self.payments.filter_by(
            payment_status=PaymentStatus.COMPLETED
        ).all())
        
        if total_paid >= self.total_amount:
            self.status = InvoiceStatus.PAID
        elif total_paid > 0:
            self.status = InvoiceStatus.PARTIALLY_PAID
        elif datetime.utcnow() > self.due_date:
            self.status = InvoiceStatus.OVERDUE
        
        await db.commit()

    # Helper Methods for Analysis
    @classmethod
    async def get_invoice_stats(cls, db, user_id=None, shop_id=None, start_date=None, end_date=None):
        """Get invoice statistics"""
        query = db.query(cls)
        if user_id:
            query = query.filter_by(fake_user_id=user_id)
        if shop_id:
            query = query.filter_by(shop_id=shop_id)
        if start_date:
            query = query.filter(cls.issue_date >= start_date)
        if end_date:
            query = query.filter(cls.issue_date <= end_date)
        
        invoices = await query.all()
        return {
            'total_invoices': len(invoices),
            'total_amount': sum(inv.total_amount for inv in invoices),
            'paid_invoices': len([inv for inv in invoices if inv.status == InvoiceStatus.PAID]),
            'overdue_invoices': len([inv for inv in invoices if inv.status == InvoiceStatus.OVERDUE]),
            'average_amount': sum(inv.total_amount for inv in invoices) / len(invoices) if invoices else 0,
            'status_breakdown': {
                status: len([inv for inv in invoices if inv.status == status])
                for status in InvoiceStatus
            }
        }
