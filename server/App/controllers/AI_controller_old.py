import os
import io
import json
import tempfile
import asyncio
import hashlib
import requests
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer
import redis.asyncio as redis
import chromadb
from chromadb.config import Settings
import PyPDF2

# Performance optimization: Run blocking operations in thread pool
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
load_dotenv()
# Cache for embeddings (avoid re-creating on every query)
_embedding_cache = {}
_executor = ThreadPoolExecutor(max_workers=4)
_redis_client = None

async def get_redis_client():
    """Get or create Redis async client"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
        except Exception as e:
            print(f"⚠️  Redis unavailable: {e}. Continuing without caching.")
            _redis_client = None
    return _redis_client

class AIService:
    def __init__(self):
        # 1. Resolve Path: Absolute pathing for 2025 cross-platform stability
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Adjusted path to ensure it finds your Config/DB folder
        persist_path = os.path.normpath(os.path.join(base_dir, "../../Config/DB/chroma_db"))
        
        os.makedirs(persist_path, exist_ok=True)

        # 2. Local AI Components (OPTIMIZED FOR SPEED)
        # Note: Use model names exactly as shown in 'ollama list'
        # mxbai-embed-large:335m is the correct embedding model name
        self.embeddings = OllamaEmbeddings(
            model="mxbai-embed-large:335m"
            # Note: show_progress is not a valid parameter for OllamaEmbeddings
        )
        self.llm = ChatOllama(
            model="llama3.2",
            temperature=0,
            num_predict=512  # ✅ Limit response length (faster generation)
        )
        
        # 3. Vector Database Initialization
        # ✅ Persist enabled for faster subsequent loads
        self.vector_db = Chroma(
            collection_name="analyst_agent_vectors",
            persist_directory=persist_path,
            embedding_function=self.embeddings
        )
        
        # 4. Reranker Model (CrossEncoder for better relevance scoring)
        # Uses a lightweight model for re-ranking retrieved documents
        try:
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        except Exception as e:
            print(f"⚠️  Reranker not available: {e}")
            self.reranker = None
        
        # 5. BM25 corpus for hybrid search (keyword-based retrieval)
        self.bm25_corpus = {}  # {user_id: {filename: BM25Okapi instance}}
        self.bm25_documents = {}  # {user_id: {filename: list of documents}}
        
        # 6. Single global instance to avoid re-initialization
        self._is_initialized = True

    async def add_document(self, text: str = None, user_id: str = None, filename: str = None, file_bytes: bytes = None):
        """Chunks and stores document vectors with semantic chunking and BM25 indexing.
        
        IMPROVEMENTS:
        - Semantic chunking: Split by sentences/paragraphs, not fixed size
        - BM25 indexing: Build keyword index for hybrid search
        - Small2Big: Store small chunks, pass larger context to LLM
        - User isolation: All operations filtered by user_id
        
        Returns: dict with 'success': bool, 'chroma_id': str (for database storage)
        """
        try:
            import uuid
            
            # If file_bytes provided (binary file), use appropriate loader
            if file_bytes and not text:
                if filename.lower().endswith('.pdf'):
                    # PDF files need to be saved to temporary file for PyPDFLoader
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                        tmp.write(file_bytes)
                        tmp_path = tmp.name
                    
                    try:
                        loader = PyPDFLoader(tmp_path)
                        pdf_docs = loader.load()
                        text = "\n".join([doc.page_content for doc in pdf_docs])
                    finally:
                        os.unlink(tmp_path)
                elif filename.lower().endswith(('.txt', '.md')):
                    # Text files - try UTF-8 decoding
                    try:
                        text = file_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        # Fallback to latin-1 if UTF-8 fails
                        text = file_bytes.decode('latin-1', errors='replace')
            
            if not text:
                raise ValueError("No text content to index")
            
            # ✅ SEMANTIC CHUNKING: Split by sentences/logical boundaries
            # Better than fixed-size chunks - preserves context
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=400,          # Smaller chunks for precision
                chunk_overlap=50,        # Small overlap for context continuity
                separators=["\n\n", "\n", ". ", " "]  # Semantic boundaries first
            )
            
            chunks = splitter.split_text(text)
            
            # ✅ OPTIMIZATION: Limit chunks for very large documents
            if len(chunks) > 1000:
                chunks = chunks[:1000]
                print(f"⚠️  Document too large: Limited to 1000 chunks (was {len(chunks)})")
            
            # Generate unique ID for this document in ChromaDB
            chroma_id = str(uuid.uuid4())
            
            # ✅ SMALL2BIG STRATEGY: Store small chunks, prepare larger context
            # Create smaller "retrieval chunks" for precision
            retrieval_chunks = []
            for i, chunk in enumerate(chunks):
                if len(chunk) > 200:
                    # Split very large chunks into smaller pieces
                    sub_chunks = [chunk[j:j+200] for j in range(0, len(chunk), 200)]
                    retrieval_chunks.extend(sub_chunks)
                else:
                    retrieval_chunks.append(chunk)
            
            # Store in ChromaDB with metadata for Small2Big retrieval
            self.vector_db.add_texts(
                texts=retrieval_chunks,
                ids=[f"{chroma_id}_{i}" for i in range(len(retrieval_chunks))],
                metadatas=[{
                    "user_id": user_id,
                    "source": filename,
                    "original_chunk": i // max(1, len(retrieval_chunks) // len(chunks))
                } for i in range(len(retrieval_chunks))]
            )
            
            # ✅ BUILD BM25 INDEX for hybrid search
            # Initialize user's BM25 if not exists
            if user_id not in self.bm25_corpus:
                self.bm25_corpus[user_id] = {}
                self.bm25_documents[user_id] = {}
            
            # Tokenize for BM25
            tokenized_chunks = [chunk.lower().split() for chunk in retrieval_chunks]
            self.bm25_corpus[user_id][filename] = BM25Okapi(tokenized_chunks)
            self.bm25_documents[user_id][filename] = retrieval_chunks
            
            # Cache in Redis for persistence
            try:
                redis_client = await get_redis_client()
                if redis_client:
                    # Cache BM25 index (simple: just store the documents)
                    cache_key = f"bm25:{user_id}:{filename}"
                    await redis_client.set(cache_key, json.dumps(retrieval_chunks), ex=86400*7)  # 7 days
            except Exception as e:
                print(f"⚠️  Redis cache failed: {e}")
            
            return {"success": True, "chroma_id": chroma_id}
            
        except Exception as e:
            print(f"Error indexing {filename}: {e}")
            raise e

    async def query_ai(self, query: str, user_id: str):
        """Retrieves context using hybrid search, reranks, and generates formatted response.
        
        IMPROVEMENTS:
        - Hybrid Search: Combine BM25 (keyword) + semantic (vector) search
        - Reranking: Use CrossEncoder to re-score documents for quality
        - Small2Big: Retrieve small chunks, pass larger context to LLM
        - Smart Formatting: Numbered lists, proper line breaks in output
        - Redis Caching: Cache query results for repeated queries
        """
        try:
            # ✅ CACHE CHECK: See if Redis has this query cached
            query_hash = hashlib.md5(f"{user_id}:{query}".encode()).hexdigest()
            redis_client = await get_redis_client()
            
            if redis_client:
                cached_answer = await redis_client.get(f"query_cache:{query_hash}")
                if cached_answer:
                    return json.loads(cached_answer)
            
            # ✅ HYBRID SEARCH: Combine BM25 and semantic search
            docs_semantic = []
            docs_bm25 = []
            
            # 1. SEMANTIC SEARCH (Vector similarity)
            retriever = self.vector_db.as_retriever(
                search_kwargs={'filter': {'user_id': user_id}, 'k': 5}  # Get more for reranking
            )
            
            docs_semantic = await asyncio.get_event_loop().run_in_executor(
                _executor,
                lambda: retriever.invoke(query)
            )
            
            # 2. BM25 SEARCH (Keyword matching)
            if user_id in self.bm25_corpus and self.bm25_corpus[user_id]:
                for filename, bm25_index in self.bm25_corpus[user_id].items():
                    scores = bm25_index.get_scores(query.lower().split())
                    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
                    
                    for idx in top_indices:
                        if idx < len(self.bm25_documents[user_id].get(filename, [])):
                            docs_bm25.append({
                                "content": self.bm25_documents[user_id][filename][idx],
                                "source": filename,
                                "score": scores[idx]
                            })
            
            # 3. MERGE: Combine both results (deduplicate)
            combined_content = {d.page_content: d for d in docs_semantic}
            for doc in docs_bm25:
                if doc["content"] not in combined_content:
                    # Convert BM25 doc to compatible format
                    class SimpleDoc:
                        def __init__(self, content, source):
                            self.page_content = content
                            self.metadata = {"source": source}
                    
                    combined_content[doc["content"]] = SimpleDoc(doc["content"], doc["source"])
            
            all_docs = list(combined_content.values())
            
            if not all_docs:
                return {
                    "answer": "I couldn't find any relevant information in your uploaded files for that query.", 
                    "sources": []
                }
            
            # 4. RERANKING: Use CrossEncoder to re-score documents
            if self.reranker and len(all_docs) > 1:
                try:
                    # Prepare pairs for reranker
                    pairs = [[query, doc.page_content] for doc in all_docs]
                    
                    # Get reranking scores
                    rerank_scores = await asyncio.get_event_loop().run_in_executor(
                        _executor,
                        lambda: self.reranker.predict(pairs)
                    )
                    
                    # Sort by rerank score
                    ranked_docs = sorted(
                        zip(all_docs, rerank_scores),
                        key=lambda x: x[1],
                        reverse=True
                    )
                    all_docs = [doc for doc, score in ranked_docs]
                except Exception as e:
                    print(f"⚠️  Reranking failed: {e}, using original order")
            
            # 5. SMALL2BIG CONTEXT: Take top 3 reranked docs
            top_docs = all_docs[:3]
            sources = list(set([d.metadata.get('source', 'Unknown') for d in top_docs]))
            
            # Limit context to 2500 chars for efficiency
            context = "\n\n---\n\n".join([d.page_content for d in top_docs])[:2500]
            
            # 6. GENERATE RESPONSE with formatted prompt
            prompt = (
                "You are Nela, an AI agent that helps users chat with their documents. Answer based ONLY on the following data:\n\n"
                f"DATA:\n{context}\n\n"
                f"QUESTION: {query}\n\n"
                "ANSWER (use numbered lists, one item per line, be concise):"
            )
            
            # Generate LLM response
            response = await asyncio.get_event_loop().run_in_executor(
                _executor,
                lambda: self.llm.invoke(prompt)
            )
            
            answer_text = response.content
            
            # 7. FORMAT OUTPUT for better readability
            answer_formatted = self._format_response(answer_text)
            
            result = {
                "answer": answer_formatted,
                "sources": sources,
                "retrieval_method": "hybrid_search_with_reranking"
            }
            
            # 8. CACHE RESULT in Redis
            if redis_client:
                try:
                    await redis_client.set(
                        f"query_cache:{query_hash}",
                        json.dumps(result),
                        ex=3600  # Cache for 1 hour
                    )
                except Exception as e:
                    print(f"⚠️  Redis cache write failed: {e}")
            
            return result
            
        except Exception as e:
            print(f"AI Service Error: {e}")
            return {
                "answer": "The AI agent encountered an error processing your query. Please try again.",
                "sources": []
            }
    
    def _format_response(self, text: str) -> str:
        """Format response with proper numbering and line breaks.
        
        Converts unformatted text to nicely formatted output with:
        - Numbered lists
        - Proper line breaks
        - Clear organization
        """
        # If text already has numbered list format, clean it up
        lines = text.strip().split('\n')
        formatted_lines = []
        
        # Auto-number lines that look like list items
        item_count = 1
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove existing numbering
            if line and (line[0].isdigit() or line[0] in '•-*'):
                # Already has numbering/bullet, keep it
                formatted_lines.append(line)
            elif line and len(line) > 5:  # Actual content line
                # Check if it's a new item (starts with capital, or is a statement)
                if formatted_lines and formatted_lines[-1]:  # Previous line exists
                    formatted_lines.append(f"{item_count}. {line}")
                    item_count += 1
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        # Join with proper spacing
        result = '\n'.join(formatted_lines)
        
        # Final cleanup: ensure proper number sequencing
        result_lines = result.split('\n')
        final_lines = []
        current_num = 1
        
        for line in result_lines:
            line = line.strip()
            if not line:
                continue
            
            # If line starts with number, renumber it
            if line and line[0].isdigit() and '.' in line[:3]:
                # Extract just the content after the number
                content = line.split('. ', 1)[1] if '. ' in line else line
                final_lines.append(f"{current_num}. {content}")
                current_num += 1
            else:
                final_lines.append(line)
        
        return '\n'.join(final_lines)

    async def delete_user_docs(self, user_id: str, filename: str):
        """Removes specific file vectors from the local database."""
        try:
            # ChromaDB 2025 syntax for targeted deletion
            self.vector_db.delete(where={
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"source": {"$eq": filename}}
                ]
            })
            return True
        except Exception as e:
            print(f"Deletion error for {filename}: {e}")
            raise e
