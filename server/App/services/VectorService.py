"""
Vector Service - PostgreSQL + pgvector Implementation

Production-ready RAG backend replacing ChromaDB with:
- pgvector for vector similarity search (HNSW index)
- pg_trgm for hybrid keyword/fuzzy search
- Embedding cache to avoid recomputation
- Batch-safe, resumable ingestion
- Multi-tenant ready design
"""

import hashlib
import json
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from sqlalchemy import text, select, func, and_, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.types import Float
from sqlalchemy.exc import DBAPIError, ProgrammingError
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

from App.models.Vector_model import DocumentChunk, EmbeddingCache


class VectorStoreNotReadyError(RuntimeError):
    """Raised when pgvector schema/table/extension is not available."""


def _is_pgvector_or_schema_missing(exc: BaseException) -> bool:
    """
    Best-effort detection for common setup failures:
    - relation "document_chunks" does not exist
    - extension "vector" is not available
    """
    msg = str(exc)
    return (
        'relation "document_chunks" does not exist' in msg
        or 'relation "embedding_cache" does not exist' in msg
        or 'extension "vector" is not available' in msg
        or "vector.control" in msg
    )


class VectorService:
    """
    Production-ready vector service using PostgreSQL + pgvector.
    
    Features:
    - Hybrid search (vector + keyword)
    - Embedding cache
    - Batch ingestion
    - Multi-tenant isolation
    """
    
    def __init__(self, embedding_dim: int = 1024):
        """
        Initialize VectorService.
        
        Args:
            embedding_dim: Dimension of embeddings (default: 1024 for mxbai-embed-large:335m)
        """
        self.embedding_dim = embedding_dim
        self.batch_size = 400  # Optimal batch size for PostgreSQL
    
    async def get_embedding_from_cache(
        self, 
        db: AsyncSession, 
        content: str
    ) -> Optional[List[float]]:
        """
        Check embedding cache for existing embedding.
        
        Uses SHA256 hash of content for fast lookups.
        
        Args:
            db: Database session
            content: Text content to check
            
        Returns:
            Cached embedding if exists, None otherwise
        """
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        try:
            result = await db.execute(
                select(EmbeddingCache.embedding)
                .where(EmbeddingCache.content_hash == content_hash)
            )
        except (ProgrammingError, DBAPIError) as e:
            if _is_pgvector_or_schema_missing(e):
                raise VectorStoreNotReadyError(
                    "Vector store not initialized (missing pgvector extension and/or tables)."
                ) from e
            raise
        cached = result.scalar_one_or_none()
        
        # NOTE: cached may be a pgvector type, list, tuple, or numpy array.
        # Never use `if cached:` because arrays have ambiguous truthiness.
        if cached is not None:
            if isinstance(cached, list):
                return cached
            if isinstance(cached, tuple):
                return list(cached)
            # Convert pgvector Vector / numpy array / other iterables to list[float]
            if hasattr(cached, "__iter__") and not isinstance(cached, (str, bytes)):
                return [float(x) for x in list(cached)]
            return None
        return None
    
    async def save_embedding_to_cache(
        self,
        db: AsyncSession,
        content: str,
        embedding: List[float]
    ) -> None:
        """
        Save embedding to cache for future reuse.
        
        Args:
            db: Database session
            content: Text content
            embedding: Embedding vector
        """
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Normalize embedding to a plain python list[float] (handles numpy arrays, etc.)
        if hasattr(embedding, "__iter__") and not isinstance(embedding, (list, str, bytes)):
            embedding = [float(x) for x in list(embedding)]

        # Use SQLAlchemy insert with pgvector support
        stmt = insert(EmbeddingCache).values(
            content_hash=content_hash,
            embedding=embedding  # List of floats
        ).on_conflict_do_nothing(index_elements=['content_hash'])
        
        try:
            await db.execute(stmt)
            await db.commit()
        except (ProgrammingError, DBAPIError) as e:
            await db.rollback()
            if _is_pgvector_or_schema_missing(e):
                raise VectorStoreNotReadyError(
                    "Vector store not initialized (missing pgvector extension and/or tables)."
                ) from e
            raise
    
    async def add_chunks(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        document_id: UUID,
        chunks: List[Dict[str, any]],
        embeddings: List[List[float]]
    ) -> int:
        """
        Batch insert document chunks with embeddings.
        
        Uses UPSERT logic to handle resumable ingestion.
        Limits to 1000 chunks per document.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            document_id: Document identifier
            chunks: List of chunk dictionaries with 'content', 'metadata', 'chunk_index'
            embeddings: List of embedding vectors
            
        Returns:
            Number of chunks inserted/updated
        """
        if len(chunks) > 1000:
            chunks = chunks[:1000]
            embeddings = embeddings[:1000]
            print(f"⚠️  Document exceeded 1000 chunks limit, truncating to first 1000")
        
        # Prepare batch data with proper pgvector format
        values = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            values.append({
                'tenant_id': tenant_id,
                'document_id': document_id,
                'content': chunk['content'],
                'embedding': embedding,  # List of floats, SQLAlchemy will handle conversion
                'chunk_metadata': chunk.get('metadata', {}),  # Store as chunk_metadata in DB
                'chunk_index': chunk.get('chunk_index', i)
            })
        
        # Batch insert with UPSERT
        inserted_count = 0
        try:
            for i in range(0, len(values), self.batch_size):
                batch = values[i:i + self.batch_size]
                
                # Use SQLAlchemy insert with pgvector support
                stmt = insert(DocumentChunk).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['id'],
                    set_={
                        'embedding': stmt.excluded.embedding,
                        'content': stmt.excluded.content,
                        'chunk_metadata': stmt.excluded.chunk_metadata,
                        'updated_at': func.now()
                    }
                )
                
                await db.execute(stmt)
                inserted_count += len(batch)
            
            await db.commit()
            return inserted_count
        except (ProgrammingError, DBAPIError) as e:
            await db.rollback()
            if _is_pgvector_or_schema_missing(e):
                raise VectorStoreNotReadyError(
                    "Vector store not initialized (missing pgvector extension and/or tables)."
                ) from e
            print(f"❌ Error in batch insert: {e}")
            raise
        except Exception as e:
            await db.rollback()
            print(f"❌ Error in batch insert: {e}")
            raise
    
    async def vector_search(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        query_embedding: List[float],
        limit: int = 20,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Vector similarity search using pgvector HNSW index.
        
        Uses cosine distance (<=> operator) for similarity.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier for isolation
            query_embedding: Query embedding vector
            limit: Maximum number of results
            filters: Optional metadata filters
            
        Returns:
            List of chunks with scores
        """
        # Build query with pgvector cosine distance
        # Use raw SQL for pgvector operators (<=> for cosine distance)
        query_embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        # Build filter conditions if provided
        filter_conditions = ""
        filter_params = {}
        if filters:
            filter_parts = []
            for idx, (key, value) in enumerate(filters.items()):
                param_name = f"filter_{idx}"
                filter_parts.append(f"chunk_metadata->>'{key}' = :{param_name}")
                filter_params[param_name] = str(value)
            if filter_parts:
                filter_conditions = " AND " + " AND ".join(filter_parts)
        
        query = text(f"""
            SELECT 
                id,
                content,
                chunk_metadata,
                document_id,
                1 - (embedding <=> '{query_embedding_str}'::vector) AS score
            FROM document_chunks
            WHERE tenant_id = :tenant_id
              {filter_conditions}
            ORDER BY embedding <=> '{query_embedding_str}'::vector
            LIMIT :limit
        """)
        
        params = {
            "tenant_id": tenant_id,
            "limit": limit,
            **filter_params
        }
        
        try:
            result = await db.execute(query, params)
        except (ProgrammingError, DBAPIError) as e:
            if _is_pgvector_or_schema_missing(e):
                raise VectorStoreNotReadyError(
                    "Vector store not initialized (missing pgvector extension and/or tables)."
                ) from e
            raise
        rows = result.all()
        
        return [
            {
                'id': str(row[0]),
                'content': row[1],
                'metadata': row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {},  # Keep 'metadata' key for API compatibility
                'document_id': str(row[3]),
                'score': float(row[4]),
                'source': 'vector'
            }
            for row in rows
        ]
    
    async def keyword_search(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        query_text: str,
        limit: int = 20,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Keyword/fuzzy search using pg_trgm similarity.
        
        Uses trigram similarity for fuzzy matching.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier for isolation
            query_text: Search query text
            limit: Maximum number of results
            filters: Optional metadata filters
            
        Returns:
            List of chunks with similarity scores
        """
        # Build query with pg_trgm similarity using raw SQL
        # Escape single quotes in query_text
        escaped_query = query_text.replace("'", "''")
        
        # Build filter conditions if provided
        filter_conditions = ""
        filter_params = {}
        if filters:
            filter_parts = []
            for idx, (key, value) in enumerate(filters.items()):
                param_name = f"filter_{idx}"
                filter_parts.append(f"chunk_metadata->>'{key}' = :{param_name}")
                filter_params[param_name] = str(value)
            if filter_parts:
                filter_conditions = " AND " + " AND ".join(filter_parts)
        
        query = text(f"""
            SELECT 
                id,
                content,
                chunk_metadata,
                document_id,
                similarity(content, :query_text) AS score
            FROM document_chunks
            WHERE tenant_id = :tenant_id
              AND content % :query_text
              {filter_conditions}
            ORDER BY similarity(content, :query_text) DESC
            LIMIT :limit
        """)
        
        params = {
            "tenant_id": tenant_id,
            "query_text": query_text,
            "limit": limit,
            **filter_params
        }
        
        try:
            result = await db.execute(query, params)
        except (ProgrammingError, DBAPIError) as e:
            if _is_pgvector_or_schema_missing(e):
                raise VectorStoreNotReadyError(
                    "Vector store not initialized (missing pgvector extension and/or tables)."
                ) from e
            raise
        rows = result.all()
        
        return [
            {
                'id': str(row[0]),
                'content': row[1],
                'metadata': row[2] if isinstance(row[2], dict) else json.loads(row[2]) if row[2] else {},
                'document_id': str(row[3]),
                'score': float(row[4]),
                'source': 'keyword'
            }
            for row in rows
        ]
    
    async def hybrid_search(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        query_embedding: List[float],
        query_text: str,
        limit: int = 20,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        Performs both searches, merges results, and normalizes scores.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            query_embedding: Query embedding vector
            query_text: Search query text
            limit: Maximum number of results
            vector_weight: Weight for vector similarity (default: 0.7)
            keyword_weight: Weight for keyword similarity (default: 0.3)
            filters: Optional metadata filters
            
        Returns:
            Merged and re-ranked chunks with combined scores
        """
        # Perform both searches in parallel
        vector_results = await self.vector_search(
            db, tenant_id, query_embedding, limit=limit, filters=filters
        )
        keyword_results = await self.keyword_search(
            db, tenant_id, query_text, limit=limit, filters=filters
        )
        
        # Merge results by chunk ID
        merged = {}
        
        # Add vector results
        for result in vector_results:
            chunk_id = result['id']
            merged[chunk_id] = {
                **result,
                'vector_score': result['score'],
                'keyword_score': 0.0
            }
        
        # Add/update with keyword results
        for result in keyword_results:
            chunk_id = result['id']
            if chunk_id in merged:
                merged[chunk_id]['keyword_score'] = result['score']
            else:
                merged[chunk_id] = {
                    **result,
                    'vector_score': 0.0,
                    'keyword_score': result['score']
                }
        
        # Normalize scores and combine
        # Normalize vector scores (already 0-1 from cosine similarity)
        # Normalize keyword scores (trigram similarity is 0-1)
        for chunk_id, chunk in merged.items():
            vector_norm = chunk['vector_score']
            keyword_norm = chunk['keyword_score']
            
            # Combined score
            chunk['score'] = (vector_weight * vector_norm) + (keyword_weight * keyword_norm)
            chunk['combined_score'] = chunk['score']
        
        # Sort by combined score and return top N
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x['score'],
            reverse=True
        )[:limit]
        
        return sorted_results
    
    async def delete_document_chunks(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        document_id: UUID
    ) -> int:
        """
        Delete all chunks for a document.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            document_id: Document identifier
            
        Returns:
            Number of chunks deleted
        """
        try:
            result = await db.execute(
                DocumentChunk.__table__.delete().where(
                    and_(
                        DocumentChunk.tenant_id == tenant_id,
                        DocumentChunk.document_id == document_id
                    )
                )
            )
            await db.commit()
            return result.rowcount
        except (ProgrammingError, DBAPIError) as e:
            await db.rollback()
            if _is_pgvector_or_schema_missing(e):
                raise VectorStoreNotReadyError(
                    "Vector store not initialized (missing pgvector extension and/or tables)."
                ) from e
            raise
    
    async def get_document_chunk_count(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        document_id: UUID
    ) -> int:
        """
        Get count of chunks for a document.
        
        Args:
            db: Database session
            tenant_id: Tenant identifier
            document_id: Document identifier
            
        Returns:
            Number of chunks
        """
        try:
            result = await db.execute(
                select(func.count(DocumentChunk.id)).where(
                    and_(
                        DocumentChunk.tenant_id == tenant_id,
                        DocumentChunk.document_id == document_id
                    )
                )
            )
        except (ProgrammingError, DBAPIError) as e:
            if _is_pgvector_or_schema_missing(e):
                raise VectorStoreNotReadyError(
                    "Vector store not initialized (missing pgvector extension and/or tables)."
                ) from e
            raise
        return result.scalar() or 0
