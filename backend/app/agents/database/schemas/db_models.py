from sqlalchemy import Column, Integer, BigInteger, String, Date, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Orders(Base):
    __tablename__ = "orders"

    order_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    user_email = Column(String, nullable=True, index=True) # Linked to user account provincial.
    product = Column(String, nullable=False)
    description = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False)
    order_date = Column(Date, nullable=False)
    delivered_date = Column(Date, nullable=True)
    status = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    
    def __repr__(self):
        return f"<Order(order_id={self.order_id}, product={self.product}, status={self.status})>"

class Users(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True) # UUID as string
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(email={self.email}, name={self.full_name})>"

class CustomerRequests(Base):
    __tablename__ = "customer_requests"

    id = Column(String, primary_key=True) # UUID as string
    order_id = Column(BigInteger, ForeignKey("orders.order_id"), nullable=False)
    user_email = Column(String, nullable=False)
    request_type = Column(String, nullable=False) # 'return', 'refund', 'exchange'
    status = Column(String, default="approved") # 'approved', 'canceled'
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CustomerRequest(id={self.id}, order_id={self.order_id}, type={self.request_type}, status={self.status})>"

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False)
    role = Column(String, nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    conversation_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ChatHistory(id={self.id}, email={self.user_email}, role={self.role})>"