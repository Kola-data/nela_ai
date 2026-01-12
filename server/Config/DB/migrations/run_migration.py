#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path

# Get the server directory
# Path: server/Config/DB/migrations/run_migration.py
# We need to go up 4 levels to reach server
script_file = Path(__file__).resolve()
server_dir = script_file.parent.parent.parent.parent  # Up 4 levels to server
sys.path.insert(0, str(server_dir))

# Change to server directory
os.chdir(server_dir)

# Import models and database setup
from Config.DB.db import engine, Base
from App.models.User_model import User
from App.models.Document_model import Document
from sqlalchemy import inspect

async def run_migration():
    """Create all tables based on SQLAlchemy models"""
    
    try:
        async with engine.begin() as conn:
            print("\n📊 Creating tables from models...")
            
            # Get existing tables
            def get_tables(sync_conn):
                inspector = inspect(sync_conn)
                return inspector.get_table_names()
            
            existing_tables = await conn.run_sync(get_tables)
            print(f"   Existing tables: {len(existing_tables)}")
            for table in existing_tables:
                print(f"     • {table}")
            
            # Create all tables
            print("\n   Creating/updating tables...")
            await conn.run_sync(Base.metadata.create_all)
            
            # Get updated tables
            updated_tables = await conn.run_sync(get_tables)
            
            new_tables = set(updated_tables) - set(existing_tables)
            if new_tables:
                print(f"\n   ✅ New tables created:")
                for table in new_tables:
                    print(f"     • {table}")
            else:
                print(f"\n   ℹ️  All tables already exist")
            
            # Show current schema
            print(f"\n✅ Migration complete!")
            print(f"   Total tables: {len(updated_tables)}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)
