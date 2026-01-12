"""
Migration: Add document status tracking fields

This migration adds:
1. status column (pending, processing, completed, failed)
2. error_message column (stores failure reasons)
3. updated_at column (tracks last update time)
4. Makes chroma_id nullable (set during background processing)

Reason: Support async background document processing
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def run_migration():
    """Run the migration"""
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        try:
            print("📋 Starting migration: Add document status tracking...")
            
            # Check if columns already exist
            result = await conn.execute(
                text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'status'
                """)
            )
            
            if result.scalar():
                print("✅ Migration already applied. Skipping.")
                return
            
            # 1. Add status column with default 'completed' for existing records
            print("  → Adding 'status' column...")
            await conn.execute(
                text("""
                ALTER TABLE documents 
                ADD COLUMN status VARCHAR(50) DEFAULT 'completed' NOT NULL
                """)
            )
            
            # 2. Add error_message column
            print("  → Adding 'error_message' column...")
            await conn.execute(
                text("""
                ALTER TABLE documents 
                ADD COLUMN error_message VARCHAR(500)
                """)
            )
            
            # 3. Add updated_at column
            print("  → Adding 'updated_at' column...")
            await conn.execute(
                text("""
                ALTER TABLE documents 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE 
                DEFAULT CURRENT_TIMESTAMP NOT NULL
                """)
            )
            
            # 4. Make chroma_id nullable (it will be NULL initially for pending uploads)
            print("  → Making 'chroma_id' nullable...")
            await conn.execute(
                text("""
                ALTER TABLE documents 
                ALTER COLUMN chroma_id DROP NOT NULL
                """)
            )
            
            # Commit all changes
            await conn.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            await conn.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(run_migration())
