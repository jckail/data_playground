from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import models, schemas, database
from datetime import datetime, timedelta
from uuid import uuid4

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create_invoice/")
def create_invoice_for_shops(current_date: datetime, db: Session = Depends(get_db)):
    try:
        # Calculate the target date (30 days ago from the current_date)
        target_date = current_date - timedelta(days=30)
        
        # Query to fetch shops created 30 days ago
        query = text("""
            SELECT 
                event_metadata->>'shop_id' AS shop_id,
                event_metadata->>'user_id' AS user_id,
                event_time
            FROM global_events
            WHERE event_type = 'user_shop_create'
            AND event_time::date = :target_date
        """)
        
        results = db.execute(query, {"target_date": target_date}).fetchall()

        if not results:
            raise HTTPException(status_code=404, detail="No shops found created 30 days ago")

        # Loop through each shop record and insert an invoice
        for shop_record in results:
            # Generate a new UUID for the invoice_id
            invoice_id = uuid4()

            # Fixed invoice amount (example)
            invoice_amount = 100.0

            # Insert into user_invoices table
            new_invoice = models.UserInvoice(
                invoice_id=invoice_id,
                user_id=shop_record.user_id,
                shop_id=shop_record.shop_id,
                invoice_amount=invoice_amount,
                event_time=current_date,
                partition_key=current_date.date()  # Assuming partition key is based on the current date
            )

            db.add(new_invoice)

        db.commit()

        return {"message": "Invoices created successfully", "total_invoices": len(results)}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create invoices: {e}")

