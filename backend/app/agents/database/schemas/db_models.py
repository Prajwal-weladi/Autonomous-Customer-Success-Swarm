from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Orders(Base):
    __tablename__ = "orders"

    order_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    product = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    order_date = Column(Date, nullable=False)
    delivered_date = Column(Date, nullable=True)
    status = Column(String, nullable=False)
    
    def __repr__(self):
        return f"<Order(order_id={self.order_id}, product={self.product}, status={self.status})>"