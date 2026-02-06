from datetime import date
from app.tools.db_connection import get_db_session
from app.schemas.db_models import Orders

def seed_data():
    db = get_db_session()

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
        )
    ]

    for order in orders:
        db.add(order)

    db.commit()
    db.close()
    print("✅ Dummy orders inserted successfully!")

if __name__ == "__main__":
    seed_data()
