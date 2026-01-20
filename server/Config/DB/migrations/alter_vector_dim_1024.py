"""
Migration: change embedding vector dimension to 1024.

Your Ollama embedding model `mxbai-embed-large:335m` returns 1024-dim vectors,
but the schema was created as vector(384). This migration updates both:
- document_chunks.embedding
- embedding_cache.embedding

Safe to run multiple times: it checks the current column type first.
"""

import asyncio
from sqlalchemy import text
from Config.DB.db import AsyncSessionLocal


async def run_migration():
    async with AsyncSessionLocal() as session:
        try:
            # Detect current types
            res = await session.execute(text("""
                SELECT
                  pg_catalog.format_type(a.atttypid, a.atttypmod) AS formatted_type
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname='public' AND c.relname='document_chunks'
                  AND a.attname='embedding'
                  AND a.attnum > 0 AND NOT a.attisdropped
                LIMIT 1;
            """))
            current = (res.scalar() or "").strip()
            if current == "vector(1024)":
                print("ℹ️  document_chunks.embedding already vector(1024)")
            else:
                print(f"🔧 Altering document_chunks.embedding: {current} -> vector(1024)")
                await session.execute(text("""
                    ALTER TABLE document_chunks
                    ALTER COLUMN embedding TYPE vector(1024)
                    USING embedding::vector(1024);
                """))

            res2 = await session.execute(text("""
                SELECT
                  pg_catalog.format_type(a.atttypid, a.atttypmod) AS formatted_type
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname='public' AND c.relname='embedding_cache'
                  AND a.attname='embedding'
                  AND a.attnum > 0 AND NOT a.attisdropped
                LIMIT 1;
            """))
            current2 = (res2.scalar() or "").strip()
            if current2 == "vector(1024)":
                print("ℹ️  embedding_cache.embedding already vector(1024)")
            else:
                print(f"🔧 Altering embedding_cache.embedding: {current2} -> vector(1024)")
                await session.execute(text("""
                    ALTER TABLE embedding_cache
                    ALTER COLUMN embedding TYPE vector(1024)
                    USING embedding::vector(1024);
                """))

            # Recreate vector index if present (drop then recreate with correct opclass)
            # Note: pgvector indexes depend on type; safest is to rebuild.
            print("🔁 Rebuilding vector index (if exists)...")
            await session.execute(text("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw"))
            await session.execute(text("DROP INDEX IF EXISTS idx_chunks_embedding_ivfflat"))
            try:
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
                    ON document_chunks
                    USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 64);
                """))
                print("✅ HNSW vector index created")
            except Exception as e:
                print(f"⚠️  HNSW index creation: {e}")
                await session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat
                    ON document_chunks
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """))
                print("✅ IVFFlat vector index created (fallback)")

            await session.commit()
            print("✅ Vector dimension migration complete.")
        except Exception as e:
            await session.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_migration())
