import os
import io
import json
import tempfile
import asyncio
import hashlib
import requests
from rank_bm25 import BM25Okapi
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
            _redis_client = await redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)
        except Exception as e:
            print(f"⚠️  Redis unavailable: {e}. Continuing without caching.")
            _redis_client = None
    return _redis_client


class EmbeddingService:
    """Direct Ollama embeddings without langchain"""
    def __init__(self, model: str = "mxbai-embed-large:335m", ollama_host: str = "http://localhost:11434"):
        self.model = model
        self.ollama_host = ollama_host
        self.session = None
    
    async def embed_documents(self, texts: list) -> list:
        """Get embeddings from Ollama for a list of texts"""
        embeddings = []
        for text in texts:
            try:
                response = requests.post(
                    f"{self.ollama_host}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=60  # Increased timeout for embeddings
                )
                if response.status_code == 200:
                    embedding = response.json()["embedding"]
                    embeddings.append(embedding)
                else:
                    print(f"⚠️  Ollama embedding failed: {response.status_code}")
                    embeddings.append([0.0] * 384)  # Fallback: zero vector
            except Exception as e:
                print(f"⚠️  Ollama connection error: {e}")
                embeddings.append([0.0] * 384)  # Fallback
        return embeddings
    
    async def embed_query(self, text: str) -> list:
        """Get embedding for a single query"""
        result = await self.embed_documents([text])
        return result[0] if result else [0.0] * 384


class AIService:
    def __init__(self):
        # 1. Setup paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        persist_path = os.path.normpath(os.path.join(base_dir, "../../Config/DB/chroma_db"))
        os.makedirs(persist_path, exist_ok=True)

        # 2. Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=persist_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name="analyst_agent_vectors",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"⚠️  ChromaDB collection error: {e}")
            self.collection = self.chroma_client.get_or_create_collection(
                name="analyst_agent_vectors"
            )

        # 3. Initialize embeddings
        self.embeddings = EmbeddingService()

        # 4. Ollama LLM parameters
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.llm_model = "llama3.2"
        
        # 5. Reranker Model (disabled for CPU-only lightweight)
        self.reranker = None
        
        # 6. BM25 corpus for hybrid search
        self.bm25_corpus = {}  # {user_id: {filename: BM25Okapi instance}}
        self.bm25_documents = {}  # {user_id: {filename: list of documents}}
        
        # 7. No fallback needed - using direct Ollama only
        self.embedding_fallback = None
        
        self._is_initialized = True
        print("✅ AI Service initialized successfully")

    async def add_document(self, text: str = None, user_id: str = None, filename: str = None, file_bytes: bytes = None):
        """Chunks and stores document vectors with semantic chunking and BM25 indexing."""
        try:
            import uuid
            
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
            
            # Semantic chunking: Split by sentences/paragraphs
            chunks = self._chunk_text(text, chunk_size=400, overlap=50)
            
            # Limit chunks for very large documents
            if len(chunks) > 1000:
                chunks = chunks[:1000]
                print(f"⚠️  Document too large: Limited to 1000 chunks")
            
            # Generate unique ID
            chroma_id = str(uuid.uuid4())
            
            # Small chunks for retrieval
            retrieval_chunks = []
            for chunk in chunks:
                if len(chunk) > 200:
                    sub_chunks = [chunk[j:j+200] for j in range(0, len(chunk), 200)]
                    retrieval_chunks.extend(sub_chunks)
                else:
                    retrieval_chunks.append(chunk)
            
            # Get embeddings
            print(f"📝 Embedding {len(retrieval_chunks)} chunks...")
            embeddings = await self.embeddings.embed_documents(retrieval_chunks)
            
            # Store in ChromaDB
            ids = [f"{chroma_id}_{i}" for i in range(len(retrieval_chunks))]
            metadatas = [{
                "user_id": user_id,
                "source": filename,
                "chunk_index": i
            } for i in range(len(retrieval_chunks))]
            
            self.collection.add(
                ids=ids,
                documents=retrieval_chunks,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            # Build BM25 index
            if user_id not in self.bm25_corpus:
                self.bm25_corpus[user_id] = {}
                self.bm25_documents[user_id] = {}
            
            tokenized_chunks = [chunk.lower().split() for chunk in retrieval_chunks]
            self.bm25_corpus[user_id][filename] = BM25Okapi(tokenized_chunks)
            self.bm25_documents[user_id][filename] = retrieval_chunks
            
            # Cache in Redis
            try:
                redis_client = await get_redis_client()
                if redis_client:
                    cache_key = f"bm25:{user_id}:{filename}"
                    await redis_client.set(cache_key, json.dumps(retrieval_chunks), ex=86400*7)
            except Exception as e:
                print(f"⚠️  Redis cache failed: {e}")
            
            print(f"✅ Document '{filename}' indexed with {len(retrieval_chunks)} chunks")
            return {"success": True, "chroma_id": chroma_id}
            
        except Exception as e:
            print(f"Error indexing {filename}: {e}")
            return {"success": False, "error": str(e)}

    async def query_ai(self, query: str, user_id: str, previous_context: str = None):
        """Retrieves context using hybrid search and generates response with memory."""
        try:
            # Cache check - FAST PATH
            query_hash = hashlib.md5(f"{user_id}:{query}".encode()).hexdigest()
            redis_client = await get_redis_client()
            
            if redis_client:
                cached_answer = await redis_client.get(f"query_cache:{query_hash}")
                if cached_answer:
                    print(f"📂 Cache hit for query")
                    return json.loads(cached_answer)
            
            # Hybrid Search: Semantic + BM25
            docs_semantic = []
            docs_bm25 = []
            
            # 1. SEMANTIC SEARCH (with timeout for faster response)
            try:
                query_embedding = await self.embeddings.embed_query(query)
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=5,
                    where={"user_id": {"$eq": user_id}},
                    include=["documents", "metadatas", "distances"]
                )
                
                if results and results["documents"]:
                    for doc, metadata, distance in zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0]
                    ):
                        docs_semantic.append({
                            "content": doc,
                            "source": metadata.get("source", "Unknown"),
                            "score": 1 - distance  # Convert distance to similarity
                        })
            except Exception as e:
                print(f"⚠️  Semantic search failed: {e}")
            
            # 2. BM25 SEARCH (lightweight, fast)
            if user_id in self.bm25_corpus:
                query_tokens = query.lower().split()
                for filename, bm25_index in self.bm25_corpus[user_id].items():
                    scores = bm25_index.get_scores(query_tokens)
                    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:3]
                    
                    for idx in top_indices:
                        if idx < len(self.bm25_documents[user_id].get(filename, [])):
                            docs_bm25.append({
                                "content": self.bm25_documents[user_id][filename][idx],
                                "source": filename,
                                "score": scores[idx]
                            })
            
            # 3. MERGE RESULTS
            unique_docs = {}
            for doc in docs_semantic + docs_bm25:
                if doc["content"] not in unique_docs:
                    unique_docs[doc["content"]] = doc
                else:
                    # Combine scores
                    unique_docs[doc["content"]]["score"] = max(
                        unique_docs[doc["content"]]["score"],
                        doc["score"]
                    )
            
            all_docs = list(unique_docs.values())
            
            if not all_docs:
                return {
                    "answer": "I couldn't find any relevant information in your uploaded files for that query.",
                    "sources": []
                }
            
            # 4. SIMPLE SCORE SORT (reranking disabled for CPU-only)
            all_docs = sorted(all_docs, key=lambda x: x["score"], reverse=True)
            print(f"✅ Retrieved and sorted {len(all_docs)} documents")
            
            # 5. SMALL2BIG: Take top 3 docs
            top_docs = all_docs[:3]
            sources = list(set([d["source"] for d in top_docs]))
            context = "\n\n---\n\n".join([d["content"] for d in top_docs])[:2500]
            
            # 6. GENERATE RESPONSE (with memory context if available)
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
            
            # Call Ollama with OPTIMIZED parameters for faster response
            # Increased timeout to handle slower responses
            try:
                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "temperature": 0,
                        "num_predict": 300,  # REDUCED from 512 for faster response
                        "num_ctx": 1024,  # OPTIMIZED context size
                        "stream": False,
                        "top_k": 40,  # Sampling optimization
                        "top_p": 0.9,
                    },
                    timeout=120  # Increased timeout to 120 seconds for slower systems
                )
            except requests.exceptions.Timeout:
                print(f"⚠️  Ollama request timed out after 120 seconds")
                return {
                    "answer": "The AI response is taking longer than expected. Please try again with a shorter question or check if Ollama is processing other requests.",
                    "sources": sources
                }
            except requests.exceptions.ConnectionError as e:
                print(f"⚠️  Cannot connect to Ollama: {e}")
                return {
                    "answer": "Cannot connect to the AI service. Please ensure Ollama is running on localhost:11434.",
                    "sources": sources
                }
            except Exception as e:
                print(f"⚠️  Ollama request error: {e}")
                return {
                    "answer": f"An error occurred while generating the AI response: {str(e)}",
                    "sources": sources
                }
            
            if response.status_code != 200:
                print(f"⚠️  Ollama error: {response.status_code}")
                return {
                    "answer": "The AI agent could not generate a response. Is Ollama running?",
                    "sources": sources
                }
            
            answer_text = response.json()["response"]
            answer_formatted = self._format_response(answer_text)
            
            result = {
                "answer": answer_formatted,
                "sources": sources,
                "retrieval_method": "hybrid_search_with_reranking"
            }
            
            # Cache result
            if redis_client:
                try:
                    await redis_client.set(
                        f"query_cache:{query_hash}",
                        json.dumps(result),
                        ex=3600  # 1 hour cache
                    )
                except Exception as e:
                    print(f"⚠️  Redis cache write failed: {e}")
            
            return result
            
        except Exception as e:
            print(f"❌ AI Service Error: {e}")
            return {
                "answer": f"Error: {str(e)}",
                "sources": []
            }
    
    def _chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 50) -> list:
        """Split text into semantic chunks"""
        # Split by sentences/paragraphs first
        sentences = text.replace('\n\n', '\n').split('\n')
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [c for c in chunks if c]
    
    def _format_response(self, text: str) -> str:
        """Format response with numbered lists and proper line breaks"""
        lines = text.strip().split('\n')
        formatted = []
        item_num = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if already numbered
            if line and line[0].isdigit() and '.' in line[:3]:
                # Already numbered, keep it
                formatted.append(line)
            else:
                # Auto-number
                formatted.append(f"{item_num}. {line}")
                item_num += 1
        
        return '\n'.join(formatted)

    async def delete_user_docs(self, user_id: str, filename: str):
        """Removes specific file vectors from the database"""
        try:
            self.collection.delete(where={
                "$and": [
                    {"user_id": {"$eq": user_id}},
                    {"source": {"$eq": filename}}
                ]
            })
            
            # Also remove from BM25
            if user_id in self.bm25_corpus and filename in self.bm25_corpus[user_id]:
                del self.bm25_corpus[user_id][filename]
                del self.bm25_documents[user_id][filename]
            
            return True
        except Exception as e:
            print(f"❌ Deletion error for {filename}: {e}")
            return False
