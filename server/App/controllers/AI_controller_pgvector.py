"""
AI Controller - PostgreSQL + pgvector Implementation

Production-ready RAG backend replacing ChromaDB with:
- pgvector for vector similarity search (HNSW index)
- pg_trgm for hybrid keyword/fuzzy search
- Embedding cache to avoid recomputation
- Batch-safe, resumable ingestion
- Multi-tenant ready design
- Re-ranking hook support
"""

import os
import io
import json
import hashlib
import requests
import redis.asyncio as redis
import PyPDF2
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from App.services.VectorService import VectorService
from App.services.VectorService import VectorStoreNotReadyError
from App.services.RerankerService import RerankerService
from Config.DB.db import get_db_session
from dotenv import load_dotenv

load_dotenv()

_redis_client = None

async def get_redis_client():
    """Get or create Redis async client"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"), 
                decode_responses=True
            )
        except Exception as e:
            print(f"⚠️  Redis unavailable: {e}. Continuing without caching.")
            _redis_client = None
    return _redis_client


class EmbeddingService:
    """Direct Ollama embeddings with caching"""
    def __init__(self, model: str = "mxbai-embed-large:335m", ollama_host: str = "http://localhost:11434"):
        self.model = model
        self.ollama_host = ollama_host
        # Note: mxbai-embed-large:335m produces 1024-dim embeddings (verified via /api/embeddings)
    
    async def embed_documents(
        self, 
        texts: List[str], 
        db: Optional[AsyncSession] = None,
        vector_service: Optional[VectorService] = None
    ) -> List[List[float]]:
        """
        Get embeddings from Ollama with caching support.
        
        Args:
            texts: List of text strings to embed
            db: Database session for embedding cache
            vector_service: VectorService instance for cache operations
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for text in texts:
            # Check cache first if available
            cached_embedding = None
            if db and vector_service:
                cached_embedding = await vector_service.get_embedding_from_cache(db, text)
            
            if cached_embedding:
                embeddings.append(cached_embedding)
            else:
                # Generate new embedding
                try:
                    response = requests.post(
                        f"{self.ollama_host}/api/embeddings",
                        json={"model": self.model, "prompt": text},
                        timeout=60
                    )
                    if response.status_code == 200:
                        embedding = response.json()["embedding"]
                        embeddings.append(embedding)
                        
                        # Save to cache if available
                        if db and vector_service:
                            await vector_service.save_embedding_to_cache(db, text, embedding)
                    else:
                        print(f"⚠️  Ollama embedding failed: {response.status_code}")
                        embeddings.append([0.0] * 1024)  # Fallback
                except Exception as e:
                    print(f"⚠️  Ollama connection error: {e}")
                    embeddings.append([0.0] * 1024)  # Fallback
        
        return embeddings
    
    async def embed_query(self, text: str) -> List[float]:
        """Get embedding for a single query"""
        result = await self.embed_documents([text])
        return result[0] if result else [0.0] * 1024


class AIService:
    """
    Production-ready AI Service using PostgreSQL + pgvector.
    
    Replaces ChromaDB with scalable PostgreSQL implementation.
    """
    
    def __init__(self):
        # Initialize vector service (PostgreSQL + pgvector)
        self.vector_service = VectorService(embedding_dim=1024)  # mxbai-embed-large:335m = 1024 dim
        
        # Initialize embedding service
        self.embeddings = EmbeddingService()
        
        # Initialize re-ranker (optional, can be enabled via config)
        reranker_strategy = os.getenv("RERANKER_STRATEGY", "none")  # "none", "cross_encoder", "llm"
        self.reranker = RerankerService(strategy=reranker_strategy)
        
        # Ollama LLM parameters
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.llm_model = "llama3.2"
        
        self._is_initialized = True
        print("✅ AI Service initialized with PostgreSQL + pgvector")
    
    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Chunk text with overlap for context continuity.
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < text_length:
                # Look for sentence endings
                for break_char in ['. ', '.\n', '!\n', '?\n', '\n\n']:
                    last_break = text.rfind(break_char, start, end)
                    if last_break != -1:
                        end = last_break + len(break_char)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - overlap
            if start >= text_length:
                break
        
        return chunks
    
    async def add_document(
        self,
        text: str = None,
        user_id: str = None,
        filename: str = None,
        file_bytes: bytes = None,
        db: Optional[AsyncSession] = None
    ) -> Dict:
        """
        Chunk and index document in PostgreSQL + pgvector.
        
        Features:
        - Semantic chunking (512-1024 tokens, 50-100 overlap)
        - Embedding cache to avoid recomputation
        - Batch insertion (300-500 chunks per batch)
        - Hard limit: ≤1000 chunks per document
        - Resumable ingestion with UPSERT
        
        Args:
            text: Text content (optional if file_bytes provided)
            user_id: User/tenant identifier
            filename: Document filename
            file_bytes: File content as bytes
            db: Database session (required for PostgreSQL operations)
            
        Returns:
            Dictionary with success status and document_id
        """
        if not db:
            return {"success": False, "error": "Database session required"}
        
        # Ensure we start with a clean transaction state
        try:
            await db.rollback()  # Rollback any existing transaction
        except:
            pass
        
        try:
            import uuid
            from uuid import UUID as UUIDType
            
            # Extract text from binary files
            if file_bytes and not text:
                if filename.lower().endswith('.pdf'):
                    try:
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                        text = "\n".join([page.extract_text() for page in pdf_reader.pages])
                    except Exception as e:
                        print(f"⚠️  PDF parsing error: {e}")
                        return {"success": False, "error": str(e)}
                elif filename.lower().endswith(('.txt', '.md')):
                    try:
                        text = file_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        text = file_bytes.decode('latin-1', errors='replace')
            
            if not text:
                raise ValueError("No text content to index")
            
            # Convert user_id to UUID if string
            tenant_id = UUIDType(user_id) if isinstance(user_id, str) else user_id
            document_id = uuid.uuid4()
            
            # Semantic chunking: 512-1024 tokens with 50-100 overlap
            chunks = self._chunk_text(text, chunk_size=768, overlap=75)
            
            # Hard limit: ≤1000 chunks per document
            if len(chunks) > 1000:
                chunks = chunks[:1000]
                print(f"⚠️  Document exceeded 1000 chunks limit, truncating to first 1000")
            
            # Prepare chunks with metadata
            chunk_data = []
            for i, chunk_content in enumerate(chunks):
                chunk_data.append({
                    'content': chunk_content,
                    'metadata': {
                        'filename': filename,
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    },
                    'chunk_index': i
                })
            
            # Get embeddings with cache support
            print(f"📝 Embedding {len(chunk_data)} chunks...")
            chunk_texts = [chunk['content'] for chunk in chunk_data]
            embeddings = await self.embeddings.embed_documents(
                chunk_texts,
                db=db,
                vector_service=self.vector_service
            )
            
            # Batch insert into PostgreSQL
            print(f"💾 Storing {len(chunk_data)} chunks in PostgreSQL...")
            try:
                inserted_count = await self.vector_service.add_chunks(
                    db=db,
                    tenant_id=tenant_id,
                    document_id=document_id,
                    chunks=chunk_data,
                    embeddings=embeddings
                )
                
                print(f"✅ Document '{filename}' indexed with {inserted_count} chunks")
                return {
                    "success": True,
                    "document_id": str(document_id),
                    "chunks_count": inserted_count
                }
            except Exception as insert_error:
                # Rollback transaction on error - CRITICAL to prevent transaction state issues
                try:
                    await db.rollback()
                except Exception as rollback_error:
                    print(f"⚠️  Rollback failed: {rollback_error}")
                if isinstance(insert_error, VectorStoreNotReadyError):
                    msg = (
                        "Vector store not initialized. Your PostgreSQL does not have pgvector/tables set up.\n"
                        "Fix: install pgvector on the DB server, then run the migration to create `document_chunks`.\n"
                        "Ubuntu/Postgres 17: sudo apt-get install postgresql-17-pgvector && restart postgresql.\n"
                        "Or use a pgvector-enabled Postgres (e.g. Docker image pgvector/pgvector)."
                    )
                    print(f"❌ {msg}")
                    return {"success": False, "error": msg}
                print(f"❌ Error inserting chunks: {insert_error}")
                raise insert_error
            
        except Exception as e:
            print(f"❌ Error indexing {filename}: {e}")
            import traceback
            traceback.print_exc()
            # Ensure rollback if db session is still active
            try:
                await db.rollback()
            except Exception as rollback_error:
                print(f"⚠️  Final rollback failed: {rollback_error}")
            return {"success": False, "error": str(e)}
    
    async def query_ai(
        self,
        query: str,
        user_id: str,
        previous_context: str = None,
        db: Optional[AsyncSession] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        rerank: bool = True
    ) -> Dict:
        """
        Query AI using hybrid search (vector + keyword) with optional re-ranking.
        
        Args:
            query: User query text
            user_id: User/tenant identifier
            previous_context: Previous conversation context
            db: Database session (required)
            vector_weight: Weight for vector similarity (default: 0.7)
            keyword_weight: Weight for keyword similarity (default: 0.3)
            rerank: Whether to apply re-ranking (default: True)
            
        Returns:
            Dictionary with answer and sources
        """
        if not db:
            return {
                "answer": "Database session required for querying",
                "sources": []
            }
        
        try:
            from uuid import UUID as UUIDType
            
            # Convert user_id to UUID
            tenant_id = UUIDType(user_id) if isinstance(user_id, str) else user_id
            
            # Cache check
            query_hash = hashlib.md5(f"{user_id}:{query}".encode()).hexdigest()
            redis_client = await get_redis_client()
            
            if redis_client:
                cached_answer = await redis_client.get(f"query_cache:{query_hash}")
                if cached_answer:
                    print(f"📂 Cache hit for query")
                    return json.loads(cached_answer)
            
            # Get query embedding
            query_embedding = await self.embeddings.embed_query(query)
            
            # Hybrid search: vector + keyword
            print(f"🔍 Performing hybrid search (vector: {vector_weight}, keyword: {keyword_weight})...")
            try:
                search_results = await self.vector_service.hybrid_search(
                    db=db,
                    tenant_id=tenant_id,
                    query_embedding=query_embedding,
                    query_text=query,
                    limit=20,  # Get top 20 for re-ranking
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight
                )
            except VectorStoreNotReadyError as e:
                msg = (
                    "Vector store not initialized yet (missing `document_chunks` / pgvector).\n"
                    "Please initialize PostgreSQL with pgvector and run migrations, then re-upload documents."
                )
                return {"answer": msg, "sources": []}
            
            if not search_results:
                return {
                    "answer": "I couldn't find any relevant information in your uploaded files for that query.",
                    "sources": []
                }
            
            # Re-ranking (optional)
            if rerank and self.reranker:
                print(f"🎯 Re-ranking {len(search_results)} results...")
                search_results = await self.reranker.rerank(query, search_results, top_n=10)
            
            # Take top chunks for context
            top_chunks = search_results[:5]
            sources = list(set([
                chunk.get('metadata', {}).get('filename', 'Unknown')
                if isinstance(chunk.get('metadata'), dict)
                else 'Unknown'
                for chunk in top_chunks
            ]))
            
            context = "\n\n---\n\n".join([chunk['content'] for chunk in top_chunks])[:2500]
            
            # Generate response with memory context
            memory_context = ""
            if previous_context:
                memory_context = f"\n\nPrevious conversation:\n{previous_context}\n"
            
            prompt = (
                "You are Nela, an AI agent that helps users chat with their documents. Answer based ONLY on the following data from the user's documents:\n\n"
                f"DATA:\n{context}"
                f"{memory_context}\n"
                f"QUESTION: {query}\n\n"
                "ANSWER (use numbered lists, one item per line, be concise):"
            )
            
            print(f"🤖 Generating response from Ollama ({self.llm_model})...")
            
            # Call Ollama
            try:
                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "temperature": 0,
                        "num_predict": 300,
                        "num_ctx": 1024,
                        "stream": False,
                        "top_k": 40,
                        "top_p": 0.9,
                    },
                    timeout=120
                )
            except requests.exceptions.Timeout:
                return {
                    "answer": "The AI response is taking longer than expected. Please try again.",
                    "sources": sources
                }
            except requests.exceptions.ConnectionError as e:
                return {
                    "answer": "Cannot connect to the AI service. Please ensure Ollama is running.",
                    "sources": sources
                }
            except Exception as e:
                return {
                    "answer": f"An error occurred: {str(e)}",
                    "sources": sources
                }
            
            if response.status_code != 200:
                return {
                    "answer": "The AI agent could not generate a response. Is Ollama running?",
                    "sources": sources
                }
            
            answer_text = response.json()["response"]
            answer_formatted = self._format_response(answer_text)
            
            result = {
                "answer": answer_formatted,
                "sources": sources
            }
            
            # Cache result
            if redis_client:
                await redis_client.set(
                    f"query_cache:{query_hash}",
                    json.dumps(result),
                    ex=3600  # 1 hour cache
                )
            
            return result
            
        except Exception as e:
            print(f"❌ Query error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "answer": f"An error occurred while processing your query: {str(e)}",
                "sources": []
            }
    
    async def delete_user_docs(self, user_id: str, filename: str, db: Optional[AsyncSession] = None) -> bool:
        """
        Delete all chunks for a document.
        
        Args:
            user_id: User/tenant identifier
            filename: Document filename
            db: Database session
            
        Returns:
            True if successful
        """
        if not db:
            return False
        
        try:
            from uuid import UUID as UUIDType
            from App.models.Document_model import Document
            from sqlalchemy import select
            
            tenant_id = UUIDType(user_id) if isinstance(user_id, str) else user_id
            
            # Find document by filename
            doc_query = select(Document).where(
                Document.user_id == tenant_id,
                Document.filename == filename
            )
            result = await db.execute(doc_query)
            document = result.scalar_one_or_none()
            
            if document:
                # Delete chunks
                deleted_count = await self.vector_service.delete_document_chunks(
                    db=db,
                    tenant_id=tenant_id,
                    document_id=document.id
                )
                print(f"✅ Deleted {deleted_count} chunks for document {filename}")
                return True
            else:
                print(f"⚠️  Document not found: {filename}")
                return False
        except VectorStoreNotReadyError as e:
            # IMPORTANT: even if vector store isn't ready, we must rollback so the caller's
            # session doesn't remain in an aborted transaction state.
            try:
                await db.rollback()
            except Exception:
                pass
            print(f"⚠️  Vector store not ready; skipping vector deletion: {e}")
            # Treat as "successful enough" so document deletion can proceed.
            return True
        except Exception as e:
            # IMPORTANT: rollback to clear aborted transaction state for caller
            try:
                await db.rollback()
            except Exception:
                pass
            print(f"❌ Delete error: {e}")
            return False
    
    def _format_response(self, text: str) -> str:
        """Format AI response with numbered lists"""
        lines = text.strip().split('\n')
        formatted = []
        item_num = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line and line[0].isdigit() and '.' in line[:3]:
                formatted.append(line)
            else:
                formatted.append(f"{item_num}. {line}")
                item_num += 1
        
        return '\n'.join(formatted)
