from .base import Base, PartitionedModel
from sqlalchemy import Column, DateTime, String, ForeignKeyConstraint, JSON, Enum, Float, Integer, UUID, UniqueConstraint
from sqlalchemy.orm import relationship, backref
import uuid
from datetime import datetime, timedelta
from .enums import PaymentStatus, PaymentTerms

class Invoice(Base, PartitionedModel):
    """
    Represents an invoice issued to a user. Invoices track amounts due,
    payment terms, and payment status. They can be linked to multiple
    payments and can be used across multiple orders.
    
    Indexing Strategy:
    - Primary key (invoice_id, partition_key)
    - invoice_number is indexed for unique constraint
    - user_id is indexed for user-based queries
    - shop_id is indexed for shop-based queries
    - status is indexed for filtering by payment status
    - event_time is indexed for partitioning
    - Composite indexes for common query patterns
    
    Partitioning Strategy:
    - Hourly partitioning based on event_time for efficient querying of recent data
    - Each partition contains one hour of data
    - Older partitions can be archived or dropped based on retention policy
    """
    __tablename__ = 'invoices'
    __partitiontype__ = "hourly"  # Changed from daily to hourly
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
    user_id = Column(
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
        Enum(PaymentStatus, schema='data_playground'), 
        nullable=False, 
        default=PaymentStatus.DRAFT,
        comment="Current status of the invoice"
    )
    payment_terms = Column(
        Enum(PaymentTerms, schema='data_playground'), 
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
        "InvoicePayment",
        backref=backref("invoice", lazy="joined"),
        foreign_keys="InvoicePayment.invoice_id",
        lazy="dynamic"
    )

    __table_args__ = (
        # Unique constraint for invoice number must include partition key
        UniqueConstraint('invoice_number', 'partition_key', name='uq_invoices_number'),
        
        # Foreign key constraints must include partition key
        ForeignKeyConstraint(
            ['user_id', 'partition_key'],
            ['data_playground.users.id', 'data_playground.users.partition_key'],
            name='fk_user_invoice',
            comment="Foreign key relationship to the users table"
        ),
        ForeignKeyConstraint(
            ['shop_id', 'partition_key'],
            ['data_playground.shops.id', 'data_playground.shops.partition_key'],
            name='fk_invoice_shop',
            comment="Foreign key relationship to the shops table"
        ),
        {
            'postgresql_partition_by': 'RANGE (partition_key)',
            'schema': 'data_playground',
            'comment': 'Stores invoice data for users'
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
            user_id=user_id,
            shop_id=shop_id,
            invoice_amount=amount,
            total_amount=amount,  # Will be updated with tax and discounts
            payment_terms=payment_terms,
            issue_date=issue_date,
            due_date=due_date,
            **invoice_data
        )
        
        return invoice

    # Helper Methods for Status Management
    async def update_status(self, db):
        """Update invoice status based on payments and due date"""
        if self.status in [PaymentStatus.CANCELLED, PaymentStatus.REFUNDED]:
            return
        
        total_paid = sum(p.amount for p in await self.payments.filter_by(
            status=PaymentStatus.COMPLETED
        ).all())
        
        if total_paid >= self.total_amount:
            self.status = PaymentStatus.PAID
        elif total_paid > 0:
            self.status = PaymentStatus.PARTIALLY_PAID
        elif datetime.utcnow() > self.due_date:
            self.status = PaymentStatus.OVERDUE
        
        await db.commit()

    # Helper Methods for Analysis
    @classmethod
    async def get_invoice_stats(cls, db, user_id=None, shop_id=None, start_date=None, end_date=None):
        """Get invoice statistics"""
        query = db.query(cls)
        if user_id:
            query = query.filter_by(user_id=user_id)
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
            'paid_invoices': len([inv for inv in invoices if inv.status == PaymentStatus.PAID]),
            'overdue_invoices': len([inv for inv in invoices if inv.status == PaymentStatus.OVERDUE]),
            'average_amount': sum(inv.total_amount for inv in invoices) / len(invoices) if invoices else 0,
            'status_breakdown': {
                status: len([inv for inv in invoices if inv.status == status])
                for status in PaymentStatus
            }
        }
