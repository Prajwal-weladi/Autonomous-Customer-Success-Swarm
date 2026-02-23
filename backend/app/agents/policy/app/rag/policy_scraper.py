"""
Policy Document Scraper and Processor using LangChain

This script:
1. Scrapes policy pages from given URLs using LangChain's WebBaseLoader
2. Extracts and cleans content with LangChain's HTML text splitters
3. Wraps them in PolicyDocument model
4. Saves raw HTML and cleaned text to disk
5. Reloads previously saved policies
6. Processes data for RAG retrieval and knowledge base using RecursiveCharacterTextSplitter

Usage:
    python -m backend.app.agents.policy.app.rag.policy_scraper
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.models import PolicyDocument, DocumentChunk
from ..core.logger import get_logger

logger = get_logger(__name__)


# URL Mapping with metadata
POLICY_URLS = {
    "returns": {
        "url": "https://stories.flipkart.com/flipkart-product-returns-2/",
        "domain": "returns",
        "title": "Flipkart Returns Policy",
    },
    "refund": {
        "url": "https://stories.flipkart.com/flipkart-product-returns-2/",
        "domain": "refund",
        "title": "Flipkart Refund Policy",
    },
    "terms": {
        "url": "https://stories.flipkart.com/terms-of-use",
        "domain": "terms",
        "title": "Flipkart Terms of Use",
    },
    "privacy": {
        "url": "https://stories.flipkart.com/privacy-policy",
        "domain": "privacy",
        "title": "Flipkart Privacy Policy",
    },
    "help": {
        "url": "https://www.flipkart.com/helpcentre",
        "domain": "general",
        "title": "Flipkart Help Centre",
    },
    "cancellation": {
        "url": "https://healthplus.flipkart.com/pages/view/return-cancellation-and-refund-policy",
        "domain": "cancellation",
        "title": "Flipkart Cancellation and Refund Policy",
    },
    "shipping": {
        "url": "https://stories.flipkart.com/flipkart-product-returns-2/",
        "domain": "shipping",
        "title": "Flipkart Shipping Policy",
    },
}


class ContentCleaner(ABC):
    """Abstract base class for content cleaning strategies."""
    
    @abstractmethod
    def clean(self, html_content: str) -> str:
        """Clean HTML content and return cleaned text."""
        pass


class BeautifulSoupCleaner(ContentCleaner):
    """Clean HTML using BeautifulSoup for structured extraction."""
    
    def clean(self, html_content: str) -> str:
        """
        Clean HTML by removing scripts, styles, and extracting main content.
        Optimized for policy documents with focus on readability.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # Remove navigation, headers, footers
            for elem in soup(["nav", "header", "footer"]):
                elem.decompose()
            
            # Get main content areas
            main_content = None
            
            # Try to find main content by common classes/ids
            for selector in ['main', 'article', '[role="main"]', '.content', '.post-content', '.container']:
                try:
                    if selector.startswith('['):
                        main_content = soup.find(attrs={'role': 'main'})
                    elif selector.startswith('.'):
                        main_content = soup.find(class_=selector[1:])
                    else:
                        main_content = soup.find(selector)
                    
                    if main_content:
                        break
                except:
                    continue
            
            # Fallback to body if no main content found
            if not main_content:
                main_content = soup.find('body') or soup
            
            # Get text with preserved structure
            text = main_content.get_text(separator='\n', strip=True)
            
            # Clean up excessive whitespace
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Error cleaning HTML with BeautifulSoup: {e}")
            # Fallback: basic text extraction
            soup = BeautifulSoup(html_content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator='\n', strip=True)



class PolicyScraper:
    """
    Scrapes policy documents from URLs using LangChain's WebBaseLoader.
    
    Features:
    - Uses LangChain's WebBaseLoader for robust HTTP requests
    - Integrates with BeautifulSoup for HTML cleaning
    - Manages storage and caching of raw and cleaned documents
    """
    
    def __init__(
        self,
        raw_dir: Optional[Path] = None,
        cleaned_dir: Optional[Path] = None,
        timeout: int = 30
    ):
        self.raw_dir = Path(raw_dir) if raw_dir else settings.RAW_POLICIES_DIR
        self.cleaned_dir = Path(cleaned_dir) if cleaned_dir else settings.CLEANED_POLICIES_DIR
        self.timeout = timeout
        self.cleaner = BeautifulSoupCleaner()
        
        # Ensure directories exist
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.cleaned_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PolicyScraper initialized - Raw dir: {self.raw_dir}, Cleaned dir: {self.cleaned_dir}")
    
    def fetch_url(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from a URL using LangChain's WebBaseLoader.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if fetch fails
        """
        try:
            logger.info(f"Fetching URL: {url}")
            
            # Use LangChain's WebBaseLoader
            loader = WebBaseLoader(
                url,
                header_template=None,
                verify_ssl=True,
            )
            
            # Load the document
            docs = loader.load()
            
            if docs:
                # WebBaseLoader returns documents with metadata and content
                logger.info(f"✅ Successfully fetched {url}")
                # Return the raw page content (before cleaning)
                return docs[0].page_content if hasattr(docs[0], 'page_content') else str(docs[0])
            else:
                logger.error(f"❌ No content returned from {url}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch {url}: {e}")
            return None
    
    def scrape_policy(
        self,
        policy_key: str,
        policy_config: Dict[str, str]
    ) -> Optional[PolicyDocument]:
        """
        Scrape a policy from URL, clean it, and save to disk.
        
        Args:
            policy_key: Unique key for the policy
            policy_config: Dict with url, domain, title
            
        Returns:
            PolicyDocument object or None if scrape fails
        """
        url = policy_config.get("url")
        domain = policy_config.get("domain")
        title = policy_config.get("title")
        
        if not url:
            logger.error(f"No URL provided for policy {policy_key}")
            return None
        
        logger.info(f"🔄 Scraping policy: {policy_key} from {url}")
        
        # Fetch HTML using LangChain
        raw_html = self.fetch_url(url)
        if not raw_html:
            return None
        
        # Clean content
        cleaned_content = self.cleaner.clean(raw_html)
        
        # Create PolicyDocument
        now = datetime.utcnow()
        policy_id = f"{domain}_{now.strftime('%Y%m%d_%H%M%S')}"
        
        policy_doc = PolicyDocument(
            policy_id=policy_id,
            policy_domain=domain,
            title=title,
            source_url=url,
            raw_content=raw_html,
            cleaned_content=cleaned_content,
            scrape_timestamp=now,
            metadata={
                "policy_key": policy_key,
                "scrape_date": now.isoformat(),
                "content_length": len(cleaned_content),
                "html_length": len(raw_html),
            }
        )
        
        # Save to disk
        self._save_policy(policy_doc)
        
        logger.info(f"✅ Successfully scraped and saved policy: {policy_key}")
        return policy_doc
    
    def scrape_all_policies(self) -> Dict[str, PolicyDocument]:
        """
        Scrape all policies from POLICY_URLS.
        
        Returns:
            Dict mapping policy_key to PolicyDocument
        """
        policies = {}
        
        for policy_key, config in POLICY_URLS.items():
            logger.info(f"Processing {policy_key}...")
            policy_doc = self.scrape_policy(policy_key, config)
            
            if policy_doc:
                policies[policy_key] = policy_doc
        
        logger.info(f"✅ Scraped {len(policies)}/{len(POLICY_URLS)} policies")
        return policies
    
    def _save_policy(self, policy_doc: PolicyDocument) -> None:
        """Save policy document to disk."""
        try:
            # Save raw HTML
            raw_file = self.raw_dir / f"{policy_doc.policy_id}.html"
            raw_file.write_text(policy_doc.raw_content, encoding='utf-8')
            logger.debug(f"Saved raw HTML: {raw_file}")
            
            # Save cleaned text
            cleaned_file = self.cleaned_dir / f"{policy_doc.policy_id}.txt"
            cleaned_file.write_text(policy_doc.cleaned_content, encoding='utf-8')
            logger.debug(f"Saved cleaned text: {cleaned_file}")
            
            # Save metadata as JSON
            metadata_file = self.cleaned_dir / f"{policy_doc.policy_id}_metadata.json"
            metadata = {
                "policy_id": policy_doc.policy_id,
                "policy_domain": policy_doc.policy_domain,
                "title": policy_doc.title,
                "source_url": policy_doc.source_url,
                "scrape_timestamp": policy_doc.scrape_timestamp.isoformat(),
                "metadata": policy_doc.metadata,
                "raw_file": str(raw_file),
                "cleaned_file": str(cleaned_file),
            }
            metadata_file.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            logger.debug(f"Saved metadata: {metadata_file}")
            
        except Exception as e:
            logger.error(f"Error saving policy {policy_doc.policy_id}: {e}")
    
    def load_policy(self, policy_id: str) -> Optional[PolicyDocument]:
        """
        Load a previously saved policy from disk.
        
        Args:
            policy_id: Policy ID to load
            
        Returns:
            PolicyDocument or None if not found
        """
        try:
            metadata_file = self.cleaned_dir / f"{policy_id}_metadata.json"
            
            if not metadata_file.exists():
                logger.warning(f"Policy metadata not found: {policy_id}")
                return None
            
            # Load metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load raw and cleaned content
            raw_file = Path(metadata["raw_file"])
            cleaned_file = Path(metadata["cleaned_file"])
            
            raw_content = raw_file.read_text(encoding='utf-8') if raw_file.exists() else ""
            cleaned_content = cleaned_file.read_text(encoding='utf-8') if cleaned_file.exists() else ""
            
            # Reconstruct PolicyDocument
            policy_doc = PolicyDocument(
                policy_id=metadata["policy_id"],
                policy_domain=metadata["policy_domain"],
                title=metadata["title"],
                source_url=metadata["source_url"],
                raw_content=raw_content,
                cleaned_content=cleaned_content,
                scrape_timestamp=datetime.fromisoformat(metadata["scrape_timestamp"]),
                metadata=metadata["metadata"]
            )
            
            logger.info(f"✅ Loaded policy: {policy_id}")
            return policy_doc
            
        except Exception as e:
            logger.error(f"Error loading policy {policy_id}: {e}")
            return None
    
    def load_all_policies(self) -> Dict[str, PolicyDocument]:
        """
        Load all saved policies from disk.
        
        Returns:
            Dict mapping policy_id to PolicyDocument
        """
        policies = {}
        
        for metadata_file in self.cleaned_dir.glob("*_metadata.json"):
            policy_id = metadata_file.stem.replace("_metadata", "")
            policy_doc = self.load_policy(policy_id)
            
            if policy_doc:
                policies[policy_id] = policy_doc
        
        logger.info(f"✅ Loaded {len(policies)} policies from disk")
        return policies



class PolicyProcessor:
    """
    Processes policy documents for RAG retrieval and knowledge base.
    
    Uses LangChain's RecursiveCharacterTextSplitter for intelligent chunking
    that respects sentence boundaries and maintains context.
    """
    
    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize LangChain's RecursiveCharacterTextSplitter
        # This splitter respects sentence boundaries and maintains context
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Separators: split on sentences first, then paragraphs, then newlines, then spaces
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )
        
        logger.info(f"PolicyProcessor initialized - Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
    
    def chunk_policy(self, policy_doc: PolicyDocument, chunk_id_prefix: str = "chunk") -> List[DocumentChunk]:
        """
        Split policy document into chunks for RAG retrieval using LangChain's splitter.
        
        LangChain's RecursiveCharacterTextSplitter:
        - Respects sentence boundaries to avoid breaking mid-sentence
        - Uses overlapping windows to preserve context
        - Supported by LangChain ecosystem for RAG applications
        
        Args:
            policy_doc: PolicyDocument to chunk
            chunk_id_prefix: Prefix for chunk IDs
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        content = policy_doc.cleaned_content
        
        # Use LangChain's RecursiveCharacterTextSplitter
        text_chunks = self.text_splitter.split_text(content)
        
        for chunk_index, chunk_text in enumerate(text_chunks):
            if chunk_text.strip():  # Only create chunks with non-empty content
                chunk = DocumentChunk(
                    chunk_id=f"{chunk_id_prefix}_{policy_doc.policy_id}_{chunk_index}",
                    policy_id=policy_doc.policy_id,
                    policy_domain=policy_doc.policy_domain,
                    content=chunk_text.strip(),
                    chunk_index=chunk_index,
                    source_url=policy_doc.source_url,
                    metadata={
                        "title": policy_doc.title,
                        "policy_key": policy_doc.metadata.get("policy_key"),
                    }
                )
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from policy {policy_doc.policy_id} using LangChain splitter")
        return chunks
    
    def process_policies(self, policies: Dict[str, PolicyDocument]) -> Dict[str, List[DocumentChunk]]:
        """
        Process multiple policies into chunks using LangChain's splitter.
        
        Args:
            policies: Dict mapping policy_key to PolicyDocument
            
        Returns:
            Dict mapping policy_key to list of DocumentChunk objects
        """
        processed = {}
        
        for policy_key, policy_doc in policies.items():
            chunks = self.chunk_policy(policy_doc)
            processed[policy_key] = chunks
        
        logger.info(f"✅ Processed {len(processed)} policies into chunks using LangChain")
        return processed
    
    def save_chunks_to_json(self, chunks_dict: Dict[str, List[DocumentChunk]], output_file: Path) -> None:
        """
        Save all chunks to a single JSON file for RAG ingestion.
        
        Args:
            chunks_dict: Dict mapping policy_key to list of chunks
            output_file: Path to save JSON file
        """
        try:
            all_chunks = []
            
            for policy_key, chunks in chunks_dict.items():
                for chunk in chunks:
                    all_chunks.append({
                        "chunk_id": chunk.chunk_id,
                        "policy_id": chunk.policy_id,
                        "policy_domain": chunk.policy_domain,
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "source_url": chunk.source_url,
                        "metadata": chunk.metadata,
                        "created_at": chunk.created_at.isoformat(),
                    })
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_chunks, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved {len(all_chunks)} chunks to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving chunks to JSON: {e}")



def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("POLICY DOCUMENT SCRAPER AND PROCESSOR")
    logger.info("=" * 80)
    
    # Initialize scraper
    scraper = PolicyScraper()
    
    # Scrape all policies
    logger.info("\n📥 SCRAPING POLICIES...")
    policies = scraper.scrape_all_policies()
    
    if not policies:
        logger.error("❌ Failed to scrape any policies")
        return
    
    logger.info(f"✅ Scraped {len(policies)} policies")
    
    # Initialize processor
    logger.info("\n⚙️ PROCESSING POLICIES...")
    processor = PolicyProcessor()
    
    # Process policies into chunks
    chunks_dict = processor.process_policies(policies)
    
    # Save chunks to JSON for RAG
    chunks_file = settings.CHUNKS_DIR / "chunks.json"
    processor.save_chunks_to_json(chunks_dict, chunks_file)
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"📊 Policies scraped: {len(policies)}")
    logger.info(f"📦 Total chunks created: {sum(len(c) for c in chunks_dict.values())}")
    logger.info(f"💾 Raw policies saved to: {scraper.raw_dir}")
    logger.info(f"💾 Cleaned policies saved to: {scraper.cleaned_dir}")
    logger.info(f"📄 Chunks JSON saved to: {chunks_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
