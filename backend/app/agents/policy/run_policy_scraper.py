"""
Quick-start Script for Policy Scraper

Run this to initialize the policy knowledge base for RAG.

Usage:
    python run_policy_scraper.py [--force-rescrape]
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.rag.rag_integration import initialize_rag_with_policies
from app.core.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Initialize policy knowledge base for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--force-rescrape',
        action='store_true',
        help='Force rescrape all policies (ignore existing cached policies)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show verbose logging'
    )
    
    args = parser.parse_args()
    
    
    logger.info("🚀 Starting Policy Knowledge Base Initialization...")
    logger.info(f"Force rescrape: {args.force_rescrape}")
    
    try:
        # Run the initialization pipeline
        result = initialize_rag_with_policies(force_rescrape=args.force_rescrape)
        
        # Print results
        print("\n" + "=" * 70)
        print("INITIALIZATION RESULTS")
        print("=" * 70)
        
        if result["status"] == "success":
            print("\n✅ SUCCESS - Policy knowledge base initialized!")
            
            # Pipeline results
            pipeline = result.get("pipeline", {})
            print(f"\n📊 PIPELINE RESULTS:")
            print(f"   • Policies scraped: {pipeline.get('policies_scraped', 0)}")
            print(f"   • Chunks created: {pipeline.get('chunks_created', 0)}")
            
            # Statistics
            stats = result.get("statistics", {})
            print(f"\n📈 STATISTICS:")
            print(f"   • Total policies: {stats.get('total_policies', 0)}")
            print(f"   • Total chunks: {stats.get('total_chunks', 0)}")
            
            if stats.get('chunks_by_domain'):
                print(f"\n   Chunks by domain:")
                for domain, count in stats['chunks_by_domain'].items():
                    print(f"      - {domain}: {count} chunks")
            
            # Validation
            validation = result.get("validation", {})
            print(f"\n✓ VALIDATION:")
            if validation.get('valid'):
                print(f"   ✅ All {validation.get('total_chunks', 0)} chunks are valid")
            else:
                print(f"   ⚠️  Found {len(validation.get('errors', []))} validation errors")
                if args.verbose and validation.get('errors'):
                    print("\n   Errors:")
                    for error in validation.get('errors', [])[:5]:
                        print(f"      - {error}")
                    if len(validation.get('errors', [])) > 5:
                        print(f"      ... and {len(validation.get('errors', [])) - 5} more")
            
            # File location
            print(f"\n📄 KNOWLEDGE BASE:")
            print(f"   • Chunks file: {result.get('chunks_file')}")
            
            print("\n" + "=" * 70)
            print("✅ Policy knowledge base is ready for RAG retrieval!")
            print("=" * 70 + "\n")
            
            return 0
        else:
            print("\n❌ FAILED - Policy knowledge base initialization failed!")
            print(f"\nErrors:")
            for error in result.get("errors", []):
                print(f"   • {error}")
            
            print("\n" + "=" * 70 + "\n")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ FATAL ERROR: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
