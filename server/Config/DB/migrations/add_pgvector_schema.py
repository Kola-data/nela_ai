"""
PostgreSQL + pgvector Migration
Replaces ChromaDB with production-ready pgvector implementation

Run this migration to set up:
- pgvector extension
- document_chunks table with HNSW index
- embedding_cache table
- pg_trgm extension for hybrid search
"""

import asyncio
from sqlalchemy import text
from Config.DB.db import AsyncSessionLocal


async def run_migration():
    """Create pgvector schema and indexes"""
    async with AsyncSessionLocal() as session:
        try:
            print("🚀 Starting pgvector migration...")
            
            # 1. Create extensions
            print("📦 Creating PostgreSQL extensions...")
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
            await session.commit()
            print("✅ Extensions created")
            
            # 2. Create document_chunks table
            print("📄 Creating document_chunks table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    tenant_id UUID NOT NULL,
                    document_id UUID NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1024),
                    chunk_metadata JSONB DEFAULT '{}'::jsonb,
                    chunk_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT now(),
                    updated_at TIMESTAMP DEFAULT now()
                )
            """))
            await session.commit()
            print("✅ document_chunks table created")
            
            # 3. Create embedding_cache table
            print("🧠 Creating embedding_cache table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    content_hash TEXT PRIMARY KEY,
                    embedding vector(1024) NOT NULL,
                    created_at TIMESTAMP DEFAULT now()
                )
            """))
            await session.commit()
            print("✅ embedding_cache table created")
            
            # 4. Create indexes
            print("🔍 Creating indexes...")
            
            # HNSW index for vector similarity search
            try:
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
                    ON document_chunks
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64)
                """))
                print("✅ HNSW vector index created")
            except Exception as e:
                print(f"⚠️  HNSW index creation: {e}")
                # Fallback to ivfflat if HNSW fails
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat
                    ON document_chunks
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100)
                """))
                print("✅ IVFFlat vector index created (fallback)")
            
            # GIN index for keyword/fuzzy search with pg_trgm
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chunks_content_trgm
                ON document_chunks
                USING gin (content gin_trgm_ops)
            """))
            print("✅ GIN trigram index created")
            
            # Metadata and tenant indexes
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chunks_tenant_doc
                ON document_chunks (tenant_id, document_id)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_chunks_tenant
                ON document_chunks (tenant_id)
            """))
            print("✅ Tenant and document indexes created")
            
            await session.commit()
            
            # 5. Verify setup
            print("🔍 Verifying setup...")
            result = await session.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM document_chunks) as chunks_count,
                    (SELECT COUNT(*) FROM embedding_cache) as cache_count
            """))
            counts = result.fetchone()
            print(f"✅ Setup complete! Chunks: {counts[0]}, Cached embeddings: {counts[1]}")
            
            print("\n🎉 pgvector migration completed successfully!")
            print("\n📋 Next steps:")
            print("   1. Update AI_controller.py to use VectorService")
            print("   2. Test ingestion pipeline")
            print("   3. Test hybrid search queries")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())
