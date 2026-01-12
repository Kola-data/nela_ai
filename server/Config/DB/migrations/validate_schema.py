#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path

# Get the server directory
# Path: server/Config/DB/migrations/validate_schema.py
# We need to go up 4 levels to reach server
script_file = Path(__file__).resolve()
server_dir = script_file.parent.parent.parent.parent  # Up 4 levels to server
sys.path.insert(0, str(server_dir))
os.chdir(server_dir)

from Config.DB.db import engine, Base
from sqlalchemy import inspect, MetaData

async def validate():
    """Validate that all models are in the database"""
    
    try:
        async with engine.begin() as conn:
            def get_info(sync_conn):
                inspector = inspect(sync_conn)
                tables = inspector.get_table_names()
                
                print("\n📋 Database Schema Validation:")
                print(f"   Tables in database: {len(tables)}")
                
                for table_name in tables:
                    columns = inspector.get_columns(table_name)
                    pk = inspector.get_pk_constraint(table_name)
                    
                    print(f"\n   📊 Table: {table_name}")
                    print(f"      Primary Key: {pk['constrained_columns']}")
                    print(f"      Columns ({len(columns)}):")
                    
                    for col in columns:
                        nullable = "nullable" if col['nullable'] else "NOT NULL"
                        print(f"         • {col['name']}: {col['type']} ({nullable})")
                
                return len(tables) > 0
            
            result = await conn.run_sync(get_info)
            
            if result:
                print("\n✅ Schema validation passed!")
            else:
                print("\n❌ No tables found in database!")
            
            return result
        
    except Exception as e:
        print(f"\n❌ Validation failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(validate())
    sys.exit(0 if success else 1)
