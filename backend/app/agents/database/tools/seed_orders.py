"""
Script to seed the database with sample orders.
Run this after creating tables.
"""

from datetime import date
from app.agents.database.tools.db_connection import get_db_session
from app.agents.database.schemas.db_models import Orders


def seed_data():
    """Seed database with sample order data"""
    db = get_db_session()

    try:
        # Clear existing data (optional)
        from app.agents.database.schemas.db_models import CustomerRequests
        db.query(CustomerRequests).delete()
        db.query(Orders).delete()
        
        # Sample orders
        orders = [
            Orders(
                order_id=7845,
                user_id="U101",
                user_email="tester123@example.com",
                product="Nike Shoes",
                description="Nike Air Max running shoes",
                quantity=1,
                order_date=date(2026, 1, 28),
                delivered_date=date(2026, 2, 1),
                status="Delivered",
                amount=8500
            ),
            Orders(
                order_id=7846,
                user_id="U102",
                user_email="example@test.com",
                product="Adidas T-Shirt",
                description="Cotton Adidas T-Shirt",
                quantity=2,
                order_date=date(2026, 1, 25),
                delivered_date=date(2026, 1, 30),
                status="Delivered",
                amount=2400
            ),
            Orders(
                order_id=7847,
                user_id="U103",
                user_email="tester123@example.com",
                product="Puma Jacket",
                description="Puma windbreaker jacket",
                quantity=1,
                order_date=date(2026, 1, 20),
                delivered_date=None,
                status="Shipped",
                amount=4500
            ),
            Orders(
                order_id=287899092720,
                user_id="U107",
                user_email="tester123@example.com",
                product="Headphones",
                description="High fidelity noise cancelling",
                quantity=1,
                order_date=date(2026, 2, 18),
                delivered_date=date(2026, 2, 21),
                status="Delivered",
                amount=9000
            ),
            Orders(
                order_id=7848,
                user_id="U104",
                product="Red Tape Shoes",
                description="Formal leather shoes",
                quantity=1,
                order_date=date(2026, 1, 25),
                delivered_date=date(2026, 2, 4),
                status="Delivered",
                amount=3200
            ),
            Orders(
                order_id=7849,
                user_id="U105",
                product="Reebok Sneakers",
                description="Classic Reebok sneakers",
                quantity=1,
                order_date=date(2025, 12, 15),
                delivered_date=date(2025, 12, 20),
                status="Delivered",
                amount=2900
            ),
            Orders(
                order_id=7850,
                user_id="U106",
                product="Under Armour Hoodie",
                description="Fleece hoodie for winter",
                quantity=1,
                order_date=date(2026, 2, 1),
                delivered_date=None,
                status="Processing",
                amount=3800
            )
        ]

        # Add orders to database
        for order in orders:
            db.add(order)

        db.commit()
        print("✅ Dummy orders inserted successfully!")
        print(f"   Total orders seeded: {len(orders)}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()