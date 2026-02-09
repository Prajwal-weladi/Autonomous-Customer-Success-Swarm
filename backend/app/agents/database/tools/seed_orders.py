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
        db.query(Orders).delete()
        
        # Sample orders
        orders = [
            Orders(
                order_id=7845,
                user_id="U101",
                product="Nike Shoes",
                size=9,
                order_date=date(2026, 1, 28),
                delivered_date=date(2026, 2, 1),
                status="Delivered"
            ),
            Orders(
                order_id=7846,
                user_id="U102",
                product="Adidas T-Shirt",
                size=42,
                order_date=date(2026, 1, 25),
                delivered_date=date(2026, 1, 30),
                status="Delivered"
            ),
            Orders(
                order_id=7847,
                user_id="U103",
                product="Puma Jacket",
                size=40,
                order_date=date(2026, 1, 20),
                delivered_date=None,
                status="Shipped"
            ),
            Orders(
                order_id=7848,
                user_id="U104",
                product="Red Tape Shoes",
                size=10,
                order_date=date(2026, 1, 25),
                delivered_date=date(2026, 2, 4),
                status="Delivered"
            ),
            Orders(
                order_id=7849,
                user_id="U105",
                product="Reebok Sneakers",
                size=8,
                order_date=date(2025, 12, 15),
                delivered_date=date(2025, 12, 20),
                status="Delivered"
            ),
            Orders(
                order_id=7850,
                user_id="U106",
                product="Under Armour Hoodie",
                size=44,
                order_date=date(2026, 2, 1),
                delivered_date=None,
                status="Processing"
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