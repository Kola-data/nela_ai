"""
Migration: Add conversation tables for memory support
Creates tables for storing conversation history and sessions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

async def run_migration():
    """Run the migration to add conversation tables using SQL"""
    from sqlalchemy import text
    from Config.DB.db import AsyncSessionLocal
    
    try:
        async with AsyncSessionLocal() as session:
            # Create conversations table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    query_embedding_hash VARCHAR(64),
                    context_sources TEXT,
                    relevance_score FLOAT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                )
            """))
            
            # Create index on conversations
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
                ON conversations(user_id)
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
                ON conversations(created_at DESC)
            """))
            
            # Create conversation_sessions table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255),
                    description TEXT,
                    message_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    ended_at TIMESTAMP WITH TIME ZONE
                )
            """))
            
            # Create indexes on conversation_sessions
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id 
                ON conversation_sessions(user_id)
            """))
            
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_conversation_sessions_is_active 
                ON conversation_sessions(is_active)
            """))
            
            await session.commit()
            print("✅ Conversation tables created successfully!")
            return True
            
    except Exception as e:
        error_msg = str(e).lower()
        print(f"⚠️  Migration result: {e}")
        # Table might already exist, which is fine
        if "already exists" in error_msg or "duplicate" in error_msg:
            print("✅ Tables already exist")
            return True
        # Ignore if it's just about indexes already existing
        if "index" in error_msg and ("already exists" in error_msg or "duplicate" in error_msg):
            print("✅ Indexes already exist")
            return True
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(run_migration())
    exit(0 if success else 1)
