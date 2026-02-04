"""
RAG service manager coordinating all components.
"""
from typing import Optional
import time

from app.core.config import settings
from app.core.logger import setup_logger
from app.core.models import QueryRequest, QueryResponse
from app.rag.embedding import EmbeddingGenerator, FAISSVectorStore
from app.rag.llm import OllamaClient
from app.rag.pipeline import AdvancedRAGPipeline
from app.rag.document_processor import DocumentProcessor
from scripts.scrapper import FlipkartPolicyScraper


logger = setup_logger(__name__)


class RAGService:
    """Service managing the complete RAG pipeline."""
    
    _instance: Optional['RAGService'] = None
    
    def __init__(self):
        self.embedding_generator: Optional[EmbeddingGenerator] = None
        self.vector_store: Optional[FAISSVectorStore] = None
        self.llm_client: Optional[OllamaClient] = None
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
            
            # Initialize pipeline
            self.pipeline = AdvancedRAGPipeline(
                vector_store=self.vector_store,
                llm_client=self.llm_client
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
    
    def reindex(self, force_rescrape: bool = False) -> dict:
        """
        Rebuild the vector index.
        
        Args:
            force_rescrape: Whether to force rescraping of policies
        
        Returns:
            Dictionary with reindexing statistics
        """
        logger.info(f"Starting reindexing (force_rescrape={force_rescrape})")
        start_time = time.time()
        
        try:
            # Initialize scraper
            scraper = FlipkartPolicyScraper()
            
            # Get policies
            if force_rescrape:
                logger.info("Force rescraping policies...")
                policies = scraper.scrape_all_policies()
            else:
                logger.info("Loading existing policies...")
                policies = scraper.load_existing_policies()
                
                if not policies:
                    logger.info("No existing policies found, scraping...")
                    policies = scraper.scrape_all_policies()
            
            if not policies:
                raise RuntimeError("No policies available for indexing")
            
            # Process documents into chunks
            processor = DocumentProcessor()
            chunks = processor.process_documents(policies)
            processor.save_chunks(chunks)
            
            # Build index
            if self.vector_store is None:
                self.embedding_generator = EmbeddingGenerator()
                self.vector_store = FAISSVectorStore(self.embedding_generator)
            
            self.vector_store.build_index(chunks)
            self.vector_store.save_index()
            
            # Reinitialize pipeline with new index
            if self.llm_client is None:
                self.llm_client = OllamaClient()
            
            self.pipeline = AdvancedRAGPipeline(
                vector_store=self.vector_store,
                llm_client=self.llm_client
            )
            
            elapsed = time.time() - start_time
            
            stats = {
                "status": "success",
                "documents_processed": len(policies),
                "chunks_created": len(chunks),
                "embeddings_generated": len(chunks),
                "duration_seconds": elapsed
            }
            
            logger.info(f"Reindexing completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Reindexing failed: {str(e)}")
            raise
    
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