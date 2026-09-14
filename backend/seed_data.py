import asyncio
from database import customers_collection

async def seed():
    existing = await customers_collection.count_documents({})
    if existing > 0:
        print("Data already exists, skipping seed.")
        return

    dummy_customers = [
        {"customer_id": "CUST001", "name": "Rahul Sharma", "email": "rahul@example.com", "order_id": "ORD101", "order_status": "pending", "amount": 2500},
        {"customer_id": "CUST002", "name": "Priya Singh", "email": "priya@example.com", "order_id": "ORD102", "order_status": "delivered", "amount": 1800},
        {"customer_id": "CUST003", "name": "Amit Verma", "email": "amit@example.com", "order_id": "ORD103", "order_status": "shipped", "amount": 3200},
    ]

    await customers_collection.insert_many(dummy_customers)
    print("Dummy data inserted successfully!")

if __name__ == "__main__":
    asyncio.run(seed())