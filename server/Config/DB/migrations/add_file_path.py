"""
Migration: Add file_path column to documents table
Purpose: Track the physical location of uploaded files
Date: 2024-12-27
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine
import asyncio


async def run_migration(engine: Engine):
    """Run the migration to add file_path column."""
    
    print("🔄 Starting migration: Add file_path to documents...")
    
    # Define migration SQL
    migration_sql = """
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);
    """
    
    try:
        with engine.begin() as connection:
            connection.execute(text(migration_sql))
            connection.commit()
        
        print("✅ Migration completed successfully")
        return True
    
    except Exception as e:
        if "already exists" in str(e).lower():
            print("⚠️  Column file_path already exists, skipping migration")
            return True
        else:
            print(f"❌ Migration failed: {str(e)}")
            return False


# For async support
async def run_migration_async(async_engine):
    """Run migration with async engine."""
    
    from sqlalchemy import text
    
    migration_sql = """
    ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);
    """
    
    try:
        async with async_engine.begin() as connection:
            await connection.execute(text(migration_sql))
        
        print("✅ Migration completed successfully (async)")
        return True
    
    except Exception as e:
        if "already exists" in str(e).lower():
            print("⚠️  Column file_path already exists, skipping migration")
            return True
        else:
            print(f"❌ Migration failed: {str(e)}")
            return False


if __name__ == "__main__":
    # For testing
    print("Run this migration via init_db.py or your migration framework")
