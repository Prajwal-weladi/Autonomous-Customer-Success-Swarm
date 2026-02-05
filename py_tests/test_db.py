from app.tools.db_connection import engine

try:
    connection = engine.connect()
    print("✅ Database connection successful")
    connection.close()
except Exception as e:
    print("❌ Database connection failed:", e)
