"""
Script to create database tables.
Run this before seeding data.
"""

from app.agents.database.tools.db_connection import engine
from app.schemas.db_models import Base

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")