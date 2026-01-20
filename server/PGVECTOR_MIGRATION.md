# PostgreSQL + pgvector Migration Guide

## Overview

This migration replaces ChromaDB with a production-ready PostgreSQL + pgvector implementation for the RAG backend.

## Features

✅ **Vector Similarity Search** - HNSW index with pgvector  
✅ **Hybrid Search** - Vector + keyword using pg_trgm  
✅ **Embedding Cache** - SHA256-based cache to avoid recomputation  
✅ **Batch Ingestion** - 300-500 chunks per batch, resumable  
✅ **Multi-Tenant** - Complete tenant isolation  
✅ **Re-ranking Hook** - Pluggable re-ranking interface  

## Prerequisites

1. PostgreSQL 12+ with pgvector extension
2. Python pgvector package

## Migration Steps

### 1. Install PostgreSQL Extensions

Connect to your PostgreSQL database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 2. Run Migration Script

```bash
cd server
python Config/DB/migrations/add_pgvector_schema.py
```

This will create:
- `document_chunks` table with HNSW index
- `embedding_cache` table
- All necessary indexes

### 3. Install Python Dependencies

```bash
pip install pgvector==0.3.2
```

### 4. Update Code

The code has been updated to use `AI_controller_pgvector.py` which uses PostgreSQL instead of ChromaDB.

### 5. Restart Server

Restart the FastAPI server to use the new implementation.

## Architecture

### Database Schema

**document_chunks**
- Stores document chunks with vector embeddings
- Multi-tenant with `tenant_id` isolation
- HNSW index for fast vector search
- GIN index for keyword search

**embedding_cache**
- Caches embeddings by content hash
- Avoids recomputing identical content

### Hybrid Search

1. **Vector Search**: Uses pgvector cosine distance (<=> operator)
2. **Keyword Search**: Uses pg_trgm similarity (% operator)
3. **Score Merging**: `final_score = (0.7 * vector_score) + (0.3 * keyword_score)`
4. **Re-ranking**: Optional cross-encoder or LLM-based re-ranking

### Chunking Strategy

- Chunk size: 512-1024 tokens (768 default)
- Overlap: 50-100 tokens (75 default)
- Hard limit: ≤1000 chunks per document

### Embedding Cache

- SHA256 hash of content as primary key
- Automatic cache lookup before embedding generation
- Saves significant compute for duplicate content

## Configuration

Set environment variables:

```env
# Re-ranking strategy (optional)
RERANKER_STRATEGY=none  # Options: none, cross_encoder, llm

# Hybrid search weights (optional, defaults shown)
VECTOR_WEIGHT=0.7
KEYWORD_WEIGHT=0.3
```

## Performance

- **HNSW Index**: Fast approximate nearest neighbor search
- **Batch Insertion**: 300-500 chunks per transaction
- **Embedding Cache**: Eliminates redundant computations
- **Multi-tenant**: Complete data isolation per tenant

## Notes

- ChromaDB dependencies can be removed after migration
- Old ChromaDB data will not be migrated automatically
- New documents will use PostgreSQL + pgvector
- Backward compatible with existing API endpoints
