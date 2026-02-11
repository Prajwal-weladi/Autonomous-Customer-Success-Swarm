"""
RAG service manager coordinating all components.
"""
from typing import Optional
import time

from app.agents.policy.app.core.config import settings
from app.agents.policy.app.core.logger import setup_logger
from app.agents.policy.app.core.models import QueryRequest, QueryResponse
from .embedding import EmbeddingGenerator, FAISSVectorStore
from .llm import OllamaClient, create_reranking_client
from .pipeline import AdvancedRAGPipeline
from .document_processor import DocumentProcessor


logger = setup_logger(__name__)


class RAGService:
    """Service managing the complete RAG pipeline."""
    
    _instance: Optional['RAGService'] = None
    
    def __init__(self):
        self.embedding_generator: Optional[EmbeddingGenerator] = None
        self.vector_store: Optional[FAISSVectorStore] = None
        self.llm_client: Optional[OllamaClient] = None
        self.reranking_client: Optional[OllamaClient] = None
        self.pipeline: Optional[AdvancedRAGPipeline] = None
        self._initialized = False
        
        logger.info("RAGService instance created")
    
    @classmethod
    def get_instance(cls) -> 'RAGService':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def initialize(self, force_reload: bool = False) -> None:
        """
        Initialize all RAG components.
        
        Args:
            force_reload: Force reload of index even if cached
        """
        if self._initialized and not force_reload:
            logger.info("RAG service already initialized")
            return
        
        logger.info("Initializing RAG service...")
        start_time = time.time()
        
        try:
            # Initialize embedding generator
            self.embedding_generator = EmbeddingGenerator()
            
            # Initialize LLM client
            self.llm_client = OllamaClient()
            
            # Initialize separate reranking client with llama3.2
            self.reranking_client = create_reranking_client()
            
            # Check Ollama connection
            if not self.llm_client.check_connection():
                raise RuntimeError("Cannot connect to Ollama. Please ensure Ollama is running.")
            
            # Initialize vector store
            self.vector_store = FAISSVectorStore(self.embedding_generator)
            
            # Try to load existing index
            if not force_reload and self.vector_store.load_index():
                logger.info("Loaded existing FAISS index")
            else:
                logger.warning("No existing index found or force reload requested")
                logger.info("Run reindexing to build the index")
            
            # Initialize pipeline with both clients
            self.pipeline = AdvancedRAGPipeline(
                vector_store=self.vector_store,
                llm_client=self.llm_client,
                reranking_client=self.reranking_client
            )
            
            self._initialized = True
            elapsed = time.time() - start_time
            logger.info(f"RAG service initialized successfully in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {str(e)}")
            raise
    
    def query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a query through the RAG pipeline.
        
        Args:
            request: QueryRequest object
        
        Returns:
            QueryResponse object
        """
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")
        
        if self.pipeline is None:
            raise RuntimeError("RAG pipeline not available")
        
        # Execute pipeline
        answer = self.pipeline.query(
            query=request.query,
            conversation_history=request.conversation_history,
            filter_domain=request.filter_domain
        )
        
        return QueryResponse(answer=answer)
    
    def get_health(self) -> dict:
        """
        Get health status of the RAG service.
        
        Returns:
            Dictionary with health information
        """
        health = {
            "status": "healthy" if self._initialized else "not_initialized",
            "version": "1.0.0",
            "ollama_connected": False,
            "index_loaded": False,
            "documents_indexed": 0
        }
        
        # Check Ollama connection
        if self.llm_client:
            health["ollama_connected"] = self.llm_client.check_connection()
        
        # Check index status
        if self.vector_store and self.vector_store.index is not None:
            health["index_loaded"] = True
            health["documents_indexed"] = self.vector_store.index.ntotal
        
        return health
    
    def get_statistics(self) -> dict:
        """
        Get detailed statistics about the RAG system.
        
        Returns:
            Dictionary with statistics
        """
        if not self._initialized or self.vector_store is None:
            return {"error": "Service not initialized"}
        
        return self.vector_store.get_statistics()


# Global service instance
rag_service = RAGService.get_instance()