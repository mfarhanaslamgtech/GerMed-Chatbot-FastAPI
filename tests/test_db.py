import asyncio
import logging
import sys
import os

# Add current directory to path so it can find 'src'
sys.path.append(os.getcwd())

from src.app.extensions.database import Database

async def check_connection():
    logging.basicConfig(level=logging.INFO)
    print("⏳ Connecting to MongoDB...")
    try:
        db_engine = Database()
        # Test the connection with a ping
        res = await db_engine.client.admin.command('ping')
        print(f"📡 MongoDB Response: {res}")
        print("✅ Success! Native Async PyMongo is working perfectly.")
        await db_engine.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_connection())
