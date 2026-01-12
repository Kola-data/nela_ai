import asyncio
from sqlalchemy import inspect
# Use absolute imports relative to the 'server' root directory
from db import engine, Base
from App.models import User_model, Document_model

# 1. Define a regular (sync) function for the inspector
def get_tables(sync_conn):
    # inspect(sync_conn) works here because run_sync provides a sync connection
    inspector = inspect(sync_conn)
    return inspector.get_table_names()

async def init_models():
    async with engine.begin() as conn:
        print("Creating tables...")
        # 2. Run the creation
        await conn.run_sync(Base.metadata.create_all)
        
        # 3. Use run_sync to call the sync inspection function
        live_tables = await conn.run_sync(get_tables)
        
        print("✅ Tables created successfully!")
        print(f"Total tables in DB: {len(live_tables)}")
        for table in live_tables:
            print(f" - {table}")

if __name__ == "__main__":
    asyncio.run(init_models())
