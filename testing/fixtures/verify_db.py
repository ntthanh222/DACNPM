import asyncio
import sys
from backend.database.connection import is_database_available

async def check_db():
    try:
        available = is_database_available()
        if available:
            print("Database connection pool is healthy and reachable.")
            sys.exit(0)
        else:
            print("Database connection failed.")
            sys.exit(1)
    except Exception as e:
        print(f"Error checking database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_db())
