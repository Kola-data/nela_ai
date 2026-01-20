import asyncio
from sqlalchemy import inspect
from sqlalchemy import text

# IMPORTANT: use the project's actual DB module (not a stray `db` package on sys.path)
from Config.DB.db import engine, Base

# Import models so they register with Base.metadata
# (This ensures create_all includes all ORM tables, even if not referenced elsewhere.)
from App.models import User_model, Document_model  # noqa: F401
from App.models import Vector_model  # noqa: F401

# Ensure pgvector schema/extensions exist (idempotent)
from Config.DB.migrations.add_pgvector_schema import run_migration as run_pgvector_migration

# 1. Define a regular (sync) function for the inspector
def get_tables(sync_conn):
    # inspect(sync_conn) works here because run_sync provides a sync connection
    inspector = inspect(sync_conn)
    return inspector.get_table_names()

async def init_models():
    # 0. Ensure required PostgreSQL extensions exist (uuid-ossp is needed by models)
    try:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    except Exception as e:
        msg = str(e)
        if ("extension \"vector\" is not available" in msg) or ("vector.control" in msg):
            print("\n❌ PostgreSQL pgvector extension is NOT installed on your database server.")
            print("   Your PostgreSQL instance cannot load `vector`, so `document_chunks` cannot be created.")
            print("\n✅ Fix options:")
            print("   - Install system package (Ubuntu/Postgres 17):")
            print("     sudo apt-get update && sudo apt-get install -y postgresql-17-pgvector")
            print("     sudo systemctl restart postgresql")
            print("   - Or point DATABASE_URL to a Postgres image that includes pgvector (e.g. pgvector/pgvector:pg17).")
            print("\nAfter that, re-run: ./start.sh\n")
        raise

    # 1. Ensure pgvector tables + indexes exist (safe to run multiple times)
    await run_pgvector_migration()

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
