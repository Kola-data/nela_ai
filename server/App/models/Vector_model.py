"""
Vector Database Models for PostgreSQL + pgvector

Replaces ChromaDB with production-ready pgvector implementation.
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
try:
    from pgvector.sqlalchemy import Vector
    VECTOR_AVAILABLE = True
except ImportError:
    # Fallback if pgvector not installed - use ARRAY
    from sqlalchemy import ARRAY, Float
    VECTOR_AVAILABLE = False
from Config.DB.db import Base


class DocumentChunk(Base):
    """
    Document chunk with vector embedding for similarity search.
    
    Multi-tenant safe with tenant_id isolation.
    """
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(
        Vector(1024) if VECTOR_AVAILABLE else ARRAY(Float),
        nullable=True
    )  # mxbai-embed-large:335m = 1024 dim
    chunk_metadata = Column(JSONB, default={}, nullable=False)  # Renamed from 'metadata' (SQLAlchemy reserved)
    chunk_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Composite index for tenant + document queries
    __table_args__ = (
        Index('idx_chunks_tenant_doc', 'tenant_id', 'document_id'),
    )


class EmbeddingCache(Base):
    """
    Embedding cache to avoid recomputing embeddings for identical content.
    
    Uses SHA256 hash of content as primary key for fast lookups.
    """
    __tablename__ = "embedding_cache"
    
    content_hash = Column(String(64), primary_key=True)  # SHA256 hex = 64 chars
    embedding = Column(
        Vector(1024) if VECTOR_AVAILABLE else ARRAY(Float),
        nullable=False
    )  # mxbai-embed-large:335m = 1024 dim
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
