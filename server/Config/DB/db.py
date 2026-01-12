import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine, 
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# --- Connection Pool Configuration ---
# pool_size: The number of connections to keep open always
# max_overflow: The number of connections to allow beyond pool_size during spikes
# pool_timeout: Seconds to wait before giving up on getting a connection from the pool
# pool_recycle: Seconds after which a connection is closed and replaced (prevents "stale" connections)

engine = create_async_engine(
    DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,  # Explicitly using the async-safe queue pool
    pool_size=10,                    # Keeps 10 connections ready
    max_overflow=20,                 # Allows up to 30 total connections (10 + 20)
    pool_timeout=30,                 # Wait 30s for a free connection
    pool_recycle=1800,               # Close connections older than 30 mins
    echo=False                       # Set to True to see raw SQL logs
)

# Create the session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

# Utility to get a session (useful for both scripts and web apps)
async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session

# --- Testing the Pool ---
if __name__ == "__main__":
    import asyncio

    async def check_pool_connection():
        try:
            async with AsyncSessionLocal() as session:
                # Running a query to verify the pooled connection works
                res = await session.execute(text("SELECT current_setting('max_connections');"))
                max_conns = res.scalar()
                print(f"✅ Pool initialized successfully.")
                print(f"📊 PostgreSQL Max Connections: {max_conns}")
                print(f"🔗 Pool Size: 10 (+20 overflow)")
        except Exception as e:
            print(f"❌ Pool Connection Failed: {e}")

    asyncio.run(check_pool_connection())
