import os
from asyncio import run
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv() # Loads the DATABASE_URL from .env

async def test_connection():
    engine = create_async_engine(os.getenv("DATABASE_URL"))
    print(f"Connecting to: {engine.url}")
    # Your async logic here...

if __name__ == "__main__":
    run(test_connection())
