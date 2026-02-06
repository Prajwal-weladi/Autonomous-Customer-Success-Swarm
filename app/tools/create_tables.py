from app.tools.db_connection import engine
from app.schemas.db_models import Base

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
