"""
Quick start script for Policy RAG Agent.
This script performs initial setup and verification.
"""
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.logger import setup_logger
from app.core.config import settings


logger = setup_logger(__name__)


def check_ollama():
    """Check if Ollama is running and models are available."""
    logger.info("Checking Ollama connection...")
    
    try:
        from app.rag.llm import OllamaClient
        
        client = OllamaClient()
        if client.check_connection():
            logger.info("✓ Ollama is running and accessible")
            return True
        else:
            logger.error("✗ Cannot connect to Ollama")
            return False
    except Exception as e:
        logger.error(f"✗ Ollama check failed: {str(e)}")
        return False


def scrape_policies():
    """Scrape Flipkart policies."""
    logger.info("Scraping Flipkart policies...")
    
    try:
        from scripts.scrapper import FlipkartPolicyScraper
        
        scraper = FlipkartPolicyScraper()
        
        # Check if policies already exist
        existing = scraper.load_existing_policies()
        if existing:
            logger.info(f"Found {len(existing)} existing policies")
            response = input("Rescrape policies? (y/n): ").strip().lower()
            if response != 'y':
                logger.info("Using existing policies")
                return True
        
        # Scrape policies
        policies = scraper.scrape_all_policies()
        
        if policies:
            logger.info(f"✓ Successfully scraped {len(policies)} policies")
            return True
        else:
            logger.error("✗ No policies scraped")
            return False
            
    except Exception as e:
        logger.error(f"✗ Policy scraping failed: {str(e)}")
        return False


def build_index():
    """Build FAISS index from policies."""
    logger.info("Building FAISS index...")
    
    try:
        from app.rag.service import rag_service
        
        # Initialize service
        rag_service.initialize()
        
        # Reindex
        stats = rag_service.reindex(force_rescrape=False)
        
        logger.info("✓ Index built successfully")
        logger.info(f"  Documents: {stats['documents_processed']}")
        logger.info(f"  Chunks: {stats['chunks_created']}")
        logger.info(f"  Embeddings: {stats['embeddings_generated']}")
        logger.info(f"  Duration: {stats['duration_seconds']:.2f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Index building failed: {str(e)}")
        return False


def test_query():
    """Test a sample query."""
    logger.info("Testing sample query...")
    
    try:
        from app.rag.service import rag_service
        from app.core.models import QueryRequest
        
        # Ensure service is initialized
        rag_service.initialize()
        
        # Test query
        request = QueryRequest(
            query="What is the return policy?",
            conversation_history=[]
        )
        
        response = rag_service.query(request)
        
        logger.info("✓ Query test successful")
        logger.info(f"  Answer: {response.answer[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Query test failed: {str(e)}")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("Policy RAG Agent - Quick Start Setup")
    print("=" * 60)
    print()
    
    steps = [
        ("Checking Ollama connection", check_ollama),
        ("Scraping policies", scrape_policies),
        ("Building index", build_index),
        ("Testing query", test_query),
    ]
    
    for step_name, step_func in steps:
        print(f"\n[Step] {step_name}")
        print("-" * 60)
        
        success = step_func()
        
        if not success:
            print(f"\n✗ Setup failed at: {step_name}")
            print("\nPlease check the logs and fix the issue.")
            print("\nCommon issues:")
            print("1. Ollama not running → Run 'ollama serve'")
            print("2. Models not pulled → Run 'ollama pull qwen2.5' and 'ollama pull mxbai-embed-large'")
            print("3. Dependencies missing → Run 'pip install -r requirements.txt'")
            return 1
    
    print("\n" + "=" * 60)
    print("✓ Setup completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start API server: python -m app.core.api")
    print("2. Test with: curl http://localhost:8000/policy/health")
    print("3. Query: curl -X POST http://localhost:8000/policy/query -H 'Content-Type: application/json' -d '{\"query\": \"What is the return policy?\"}'")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())