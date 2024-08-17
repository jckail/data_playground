import asyncio
from datetime import datetime, timedelta
import random
import httpx

from app.schemas import InvoiceCreate
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.helpers import process_tasks, post_request, BASE_URL, logger

async def create_fake_invoice(client, shop_id, user_id, current_date):
    try:
        invoice_data = InvoiceCreate(
            user_id=user_id,
            shop_id=shop_id,
            invoice_amount=round(random.uniform(50.0, 500.0), 2),  # Example invoice amount
            event_time=current_date,
        )

        return await post_request(
            client,
            f"{BASE_URL}/create_invoice/",
            invoice_data.dict(),  # Convert the Pydantic model to a dictionary
            f"Failed to create invoice for shop {shop_id}",
        )
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        return None

async def generate_fake_invoices(client, current_date, db: Session):
    try:
        # Calculate the target date (30 days ago from the current_date)
        target_date = current_date - timedelta(days=30)
        
        # Query to fetch shops created 30 days ago
        query = f"""
            SELECT 
                id::text,
                shop_owner_id::text
            FROM shops
            WHERE created_time::date = '{str(target_date)}'::date
        """
        
        results = db.execute(text(query)).fetchall()

        if not results:
            logger.info(f"No shops found created 30 days ago on {target_date}")
            return None

        tasks = [
            create_fake_invoice(client, shop.shop_id, shop.shop_owner_id, current_date)
            for shop in results
        ]
        
        todays_invoices = await process_tasks(client, tasks)
        logger.info(f"Generated {len(todays_invoices)} invoices for shops created on {target_date}")

        return todays_invoices
    except Exception as e:
        logger.error(f"Error generating fake invoices for date {current_date}: {e}")
        return None

if __name__ == "__main__":
    start_date = datetime(2024, 1, 1).date()
    end_date = datetime(2024, 1, 2).date()

    async def generate_fake_invoice_data(start_date, end_date):
        try:
            # Create an async HTTP client
            async with httpx.AsyncClient() as client:
                # Use get_db() in a synchronous context
                db = next(get_db())  # Get the DB session
                try:
                    for i in range((end_date - start_date).days + 1):
                        current_date = start_date + timedelta(days=i)
                        await generate_fake_invoices(client, current_date, db)
                finally:
                    db.close()  # Ensure the DB session is closed

                logger.info(f"Fake invoice generation completed from {start_date} to {end_date}")
        except Exception as e:
            logger.error(f"Error during fake invoice generation: {e}")

    asyncio.run(generate_fake_invoice_data(start_date, end_date))
