import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
import faiss
from langchain_community.embeddings import OllamaEmbeddings

from ..core.config import settings
from ..core.logger import setup_logger
from ..core.models import DocumentChunk


logger = setup_logger(__name__)


class EmbeddingGenerator:
    """Generate embeddings using Ollama."""
    
    def __init__(self, model: str = settings.EMBEDDING_MODEL):
        self.model = model
        self.embeddings = OllamaEmbeddings(
            model=model,
            base_url=settings.OLLAMA_BASE_URL
        )
        logger.info(f"Initialized EmbeddingGenerator with model '{model}'")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text
        
        Returns:
            Embedding vector
        """
        try:
            embedding = self.embeddings.embed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
        
        Returns:
            List of embedding vectors
        """
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                batch_embeddings = self.embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(
                    f"Generated embeddings for batch {i//batch_size + 1}/"
                    f"{(len(texts)-1)//batch_size + 1}"
                )
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {str(e)}")
                raise
        
        logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
        return all_embeddings


class FAISSVectorStore:
    """FAISS-based vector store for document retrieval."""
    
    def __init__(self, embedding_generator: EmbeddingGenerator):
        self.embedding_generator = embedding_generator
        self.index: Optional[faiss.Index] = None
        self.chunks: List[DocumentChunk] = []
        self.dimension: Optional[int] = None
        
        self.index_path = settings.EMBEDDINGS_DIR / "faiss_index.bin"
        self.metadata_path = settings.EMBEDDINGS_DIR / "metadata.pkl"
        
        logger.info("Initialized FAISSVectorStore")
    
    def _create_index(self, dimension: int) -> faiss.Index:
        """
        Create a new FAISS index.
        
        Args:
            dimension: Embedding dimension
        
        Returns:
            FAISS index
        """
        # Using IndexFlatIP (Inner Product) for cosine similarity
        # Normalize vectors before adding for true cosine similarity
        index = faiss.IndexFlatIP(dimension)
        logger.info(f"Created FAISS index with dimension {dimension}")
        return index
    
    def build_index(
        self,
        chunks: List[DocumentChunk],
        batch_size: int = 32
    ) -> None:
        """
        Build FAISS index from document chunks.
        
        Args:
            chunks: List of DocumentChunk objects
            batch_size: Batch size for embedding generation
        """
        if not chunks:
            logger.warning("No chunks provided for indexing")
            return
        
        logger.info(f"Building index for {len(chunks)} chunks")
        
        # Extract text content
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embedding_generator.generate_embeddings_batch(
            texts,
            batch_size=batch_size
        )
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings_array)
        
        # Create index
        self.dimension = embeddings_array.shape[1]
        self.index = self._create_index(self.dimension)
        
        # Add vectors to index
        self.index.add(embeddings_array)
        self.chunks = chunks
        
        logger.info(
            f"Built FAISS index with {self.index.ntotal} vectors, "
            f"dimension {self.dimension}"
        )
    
    def search(
        self,
        query: str,
        k: int = settings.TOP_K_RETRIEVAL,
        filter_domain: Optional[str] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Search for similar chunks.
        
        Args:
            query: Query text
            k: Number of results to return
            filter_domain: Optional domain filter
        
        Returns:
            List of (chunk, score) tuples
        """
        if self.index is None or not self.chunks:
            logger.warning("Index not initialized or empty")
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)
        query_vector = np.array([query_embedding], dtype=np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_vector)
        
        # Search
        # Search more if we need to filter
        search_k = k * 3 if filter_domain else k
        
        scores, indices = self.index.search(query_vector, search_k)
        
        # Collect results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.chunks):
                chunk = self.chunks[idx]
                
                # Apply domain filter if specified
                if filter_domain and chunk.policy_domain != filter_domain:
                    continue
                
                results.append((chunk, float(score)))
                
                if len(results) >= k:
                    break
        
        logger.debug(f"Found {len(results)} results for query")
        return results
    
    def save_index(self) -> None:
        """Save FAISS index and metadata to disk."""
        if self.index is None:
            logger.warning("No index to save")
            return
        
        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))
        
        # Save metadata
        metadata = {
            'chunks': self.chunks,
            'dimension': self.dimension
        }
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        logger.info(f"Saved index to {self.index_path}")
    
    def load_index(self) -> bool:
        """
        Load FAISS index and metadata from disk.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.index_path.exists() or not self.metadata_path.exists():
            logger.warning("Index files not found")
            return False
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_path))
            
            # Load metadata
            with open(self.metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            self.chunks = metadata['chunks']
            self.dimension = metadata['dimension']
            
            logger.info(
                f"Loaded index with {self.index.ntotal} vectors, "
                f"dimension {self.dimension}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to load index: {str(e)}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        if self.index is None:
            return {"status": "not_initialized"}
        
        domain_counts = {}
        for chunk in self.chunks:
            domain = chunk.policy_domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        return {
            "status": "initialized",
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "total_chunks": len(self.chunks),
            "domains": domain_counts
        }