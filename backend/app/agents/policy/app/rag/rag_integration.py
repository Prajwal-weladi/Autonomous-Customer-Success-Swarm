"""
Integration of Policy Scraper with RAG Service

This module provides functions to:
1. Scrape and load policies
2. Process them for RAG
3. Integrate with existing RAG service pipeline
4. Update embeddings and retrievals
"""
import logging
from pathlib import Path
from typing import Optional, Dict, List
import json

from ..rag.policy_scraper import (
    PolicyScraper,
    PolicyProcessor,
    POLICY_URLS
)
from ..core.models import PolicyDocument, DocumentChunk
from ..core.config import settings
from ..core.logger import get_logger

logger = get_logger(__name__)


class RAGPolicyIntegration:
    """
    Integrates policy scraping with RAG service.
    
    Handles the complete pipeline:
    1. Scrape policies from URLs
    2. Process and chunk
    3. Save to knowledge base
    4. Generate embeddings (when RAG service is ready)
    """
    
    def __init__(self):
        self.scraper = PolicyScraper()
        self.processor = PolicyProcessor()
        self.chunks_file = settings.CHUNKS_DIR / "chunks.json"
        logger.info("RAGPolicyIntegration initialized")
    
    def scrape_and_process(self, force_rescrape: bool = False) -> Dict[str, any]:
        """
        Complete pipeline: scrape, process, and save policies.
        
        Args:
            force_rescrape: If True, ignore existing saved policies and rescrape
            
        Returns:
            Dict with operation status and summary
        """
        logger.info("🚀 Starting policy scrape and process pipeline...")
        
        result = {
            "status": "success",
            "policies_scraped": 0,
            "chunks_created": 0,
            "errors": []
        }
        
        try:
            # Load existing policies if not forcing rescrape
            if not force_rescrape:
                logger.info("📦 Checking for existing policies...")
                existing_policies = self.scraper.load_all_policies()
                if existing_policies:
                    logger.info(f"✅ Found {len(existing_policies)} existing policies, loading...")
                    policies = existing_policies
                else:
                    logger.info("No existing policies found, scraping...")
                    policies = self.scraper.scrape_all_policies()
            else:
                logger.info("🔄 Force rescrape enabled, scraping all policies...")
                policies = self.scraper.scrape_all_policies()
            
            if not policies:
                logger.error("❌ No policies available to process")
                result["status"] = "error"
                result["errors"].append("Failed to obtain policies")
                return result
            
            result["policies_scraped"] = len(policies)
            
            # Process policies into chunks
            logger.info("⚙️ Processing policies into chunks...")
            chunks_dict = self.processor.process_policies(policies)
            
            # Count total chunks
            total_chunks = sum(len(c) for c in chunks_dict.values())
            result["chunks_created"] = total_chunks
            
            # Save chunks to JSON
            logger.info("💾 Saving chunks to JSON...")
            self.processor.save_chunks_to_json(chunks_dict, self.chunks_file)
            
            logger.info("✅ Policy scrape and process pipeline completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in pipeline: {e}", exc_info=True)
            result["status"] = "error"
            result["errors"].append(str(e))
            return result
    
    def load_chunks(self) -> Optional[List[Dict]]:
        """
        Load chunks from the saved JSON file.
        
        Returns:
            List of chunk dicts or None if file doesn't exist
        """
        try:
            if not self.chunks_file.exists():
                logger.warning(f"Chunks file not found: {self.chunks_file}")
                return None
            
            with open(self.chunks_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            
            logger.info(f"✅ Loaded {len(chunks)} chunks from {self.chunks_file}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error loading chunks: {e}")
            return None
    
    def get_chunks_by_domain(self, domain: str) -> List[Dict]:
        """
        Get all chunks for a specific policy domain.
        
        Args:
            domain: Policy domain (e.g., 'refund', 'returns', 'shipping')
            
        Returns:
            List of chunks for the domain
        """
        chunks = self.load_chunks()
        if not chunks:
            return []
        
        domain_chunks = [c for c in chunks if c.get('policy_domain') == domain]
        logger.info(f"Found {len(domain_chunks)} chunks for domain '{domain}'")
        return domain_chunks
    
    def get_policy_stats(self) -> Dict[str, any]:
        """
        Get statistics about loaded policies and chunks.
        
        Returns:
            Dict with statistics
        """
        chunks = self.load_chunks()
        policies = self.scraper.load_all_policies()
        
        stats = {
            "total_policies": len(policies) if policies else 0,
            "total_chunks": len(chunks) if chunks else 0,
            "chunks_by_domain": {},
            "policies_by_domain": {},
        }
        
        if chunks:
            for chunk in chunks:
                domain = chunk.get('policy_domain')
                stats['chunks_by_domain'][domain] = stats['chunks_by_domain'].get(domain, 0) + 1
        
        if policies:
            for policy in policies.values():
                domain = policy.policy_domain
                stats['policies_by_domain'][domain] = stats['policies_by_domain'].get(domain, 0) + 1
        
        return stats
    
    def validate_chunks(self) -> Dict[str, any]:
        """
        Validate chunks for RAG ingestion.
        
        Checks:
        - All chunks have required fields
        - Content is not empty
        - IDs are unique
        
        Returns:
            Dict with validation results
        """
        logger.info("🔍 Validating chunks...")
        chunks = self.load_chunks()
        
        result = {
            "valid": True,
            "total_chunks": len(chunks) if chunks else 0,
            "errors": [],
            "warnings": [],
        }
        
        if not chunks:
            result["warnings"].append("No chunks found to validate")
            return result
        
        seen_ids = set()
        required_fields = {'chunk_id', 'policy_id', 'policy_domain', 'content', 'source_url'}
        
        for i, chunk in enumerate(chunks):
            # Check required fields
            missing_fields = required_fields - set(chunk.keys())
            if missing_fields:
                result["valid"] = False
                result["errors"].append(f"Chunk {i}: Missing fields {missing_fields}")
            
            # Check content
            if not chunk.get('content') or not chunk['content'].strip():
                result["valid"] = False
                result["errors"].append(f"Chunk {i}: Empty content")
            
            # Check unique IDs
            chunk_id = chunk.get('chunk_id')
            if chunk_id in seen_ids:
                result["valid"] = False
                result["errors"].append(f"Chunk {i}: Duplicate ID {chunk_id}")
            seen_ids.add(chunk_id)
        
        if result["valid"]:
            logger.info(f"✅ All {len(chunks)} chunks are valid")
        else:
            logger.error(f"❌ Validation found {len(result['errors'])} errors")
        
        return result
    
    def export_chunks_for_rag(self, output_format: str = "json") -> str:
        """
        Export chunks in format suitable for RAG service.
        
        Args:
            output_format: 'json' or 'jsonl'
            
        Returns:
            Path to exported file
        """
        logger.info(f"📤 Exporting chunks for RAG in {output_format} format...")
        chunks = self.load_chunks()
        
        if not chunks:
            logger.error("No chunks to export")
            return None
        
        export_dir = settings.DATA_DIR / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        
        if output_format == "jsonl":
            # Export as JSONL (one JSON object per line)
            export_file = export_dir / "chunks.jsonl"
            with open(export_file, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    f.write(json.dumps(chunk) + '\n')
        else:
            # Export as regular JSON
            export_file = export_dir / "chunks.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported {len(chunks)} chunks to {export_file}")
        return str(export_file)


def initialize_rag_with_policies(force_rescrape: bool = False) -> Dict[str, any]:
    """
    Initialize RAG system with policies.
    
    This is the main entry point for setting up the policy knowledge base.
    
    Args:
        force_rescrape: If True, rescrape all policies
        
    Returns:
        Dict with initialization result
    """
    logger.info("🚀 Initializing RAG with policies...")
    
    integration = RAGPolicyIntegration()
    
    # Run scrape and process pipeline
    pipeline_result = integration.scrape_and_process(force_rescrape=force_rescrape)
    
    if pipeline_result["status"] == "error":
        logger.error(f"Failed to initialize RAG: {pipeline_result['errors']}")
        return pipeline_result
    
    # Validate chunks
    validation_result = integration.validate_chunks()
    
    # Get statistics
    stats = integration.get_policy_stats()
    
    return {
        "status": "success",
        "pipeline": pipeline_result,
        "validation": validation_result,
        "statistics": stats,
        "chunks_file": str(integration.chunks_file),
    }
