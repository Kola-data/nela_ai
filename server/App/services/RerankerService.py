"""
Re-ranking Service - Pluggable Re-ranking Layer

Supports multiple re-ranking strategies:
- Cross-encoder models
- LLM-based re-ranking
- External API re-ranking
"""

from typing import List, Dict, Optional
from abc import ABC, abstractmethod


class RerankerInterface(ABC):
    """Abstract interface for re-ranking implementations"""
    
    @abstractmethod
    async def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Re-rank chunks based on query relevance.
        
        Args:
            query: User query text
            chunks: List of chunk dictionaries with 'content', 'score', etc.
            
        Returns:
            Re-ranked list of chunks (sorted by relevance)
        """
        pass


class NoOpReranker(RerankerInterface):
    """No-op re-ranker that returns chunks unchanged"""
    
    async def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """Return chunks unchanged"""
        return chunks


class CrossEncoderReranker(RerankerInterface):
    """Cross-encoder based re-ranking"""
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize cross-encoder re-ranker.
        
        Args:
            model_name: HuggingFace model name for cross-encoder
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Lazy load cross-encoder model"""
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
            print(f"✅ Cross-encoder re-ranker loaded: {self.model_name}")
        except ImportError:
            print("⚠️  sentence-transformers not available, re-ranking disabled")
            self.model = None
        except Exception as e:
            print(f"⚠️  Failed to load cross-encoder: {e}")
            self.model = None
    
    async def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Re-rank chunks using cross-encoder.
        
        Args:
            query: User query text
            chunks: List of chunk dictionaries
            
        Returns:
            Re-ranked chunks with updated scores
        """
        if not self.model or not chunks:
            return chunks
        
        try:
            # Prepare pairs for cross-encoder
            pairs = [[query, chunk['content']] for chunk in chunks]
            
            # Get relevance scores
            scores = self.model.predict(pairs)
            
            # Update chunk scores
            for i, chunk in enumerate(chunks):
                chunk['rerank_score'] = float(scores[i])
                chunk['score'] = float(scores[i])  # Replace original score
            
            # Sort by rerank score
            reranked = sorted(chunks, key=lambda x: x['rerank_score'], reverse=True)
            
            return reranked
        except Exception as e:
            print(f"⚠️  Re-ranking failed: {e}, returning original order")
            return chunks


class LLMReranker(RerankerInterface):
    """LLM-based re-ranking using prompt engineering"""
    
    def __init__(self, llm_client=None):
        """
        Initialize LLM re-ranker.
        
        Args:
            llm_client: LLM client (e.g., Ollama, OpenAI)
        """
        self.llm_client = llm_client
    
    async def rerank(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        Re-rank chunks using LLM relevance scoring.
        
        Args:
            query: User query text
            chunks: List of chunk dictionaries
            
        Returns:
            Re-ranked chunks
        """
        if not self.llm_client or not chunks:
            return chunks
        
        # TODO: Implement LLM-based re-ranking
        # This would involve prompting the LLM to score each chunk's relevance
        # For now, return chunks unchanged
        return chunks


class RerankerService:
    """
    Re-ranking service with pluggable backends.
    
    Usage:
        reranker = RerankerService(strategy="cross_encoder")
        reranked = await reranker.rerank(query, chunks)
    """
    
    def __init__(self, strategy: str = "none"):
        """
        Initialize re-ranker service.
        
        Args:
            strategy: Re-ranking strategy ("none", "cross_encoder", "llm")
        """
        self.strategy = strategy
        self.reranker = self._create_reranker(strategy)
    
    def _create_reranker(self, strategy: str) -> RerankerInterface:
        """Create re-ranker instance based on strategy"""
        if strategy == "none" or strategy is None:
            return NoOpReranker()
        elif strategy == "cross_encoder":
            return CrossEncoderReranker()
        elif strategy == "llm":
            return LLMReranker()
        else:
            print(f"⚠️  Unknown re-ranking strategy: {strategy}, using no-op")
            return NoOpReranker()
    
    async def rerank(self, query: str, chunks: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        Re-rank chunks and return top N results.
        
        Args:
            query: User query text
            chunks: List of chunk dictionaries
            top_n: Number of top results to return
            
        Returns:
            Top N re-ranked chunks
        """
        if not chunks:
            return []
        
        # Limit chunks for re-ranking (re-ranking is expensive)
        chunks_to_rerank = chunks[:20] if len(chunks) > 20 else chunks
        
        # Re-rank
        reranked = await self.reranker.rerank(query, chunks_to_rerank)
        
        # Return top N
        return reranked[:top_n]
