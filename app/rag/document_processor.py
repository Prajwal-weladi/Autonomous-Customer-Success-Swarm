"""
Document processing and chunking pipeline.
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.logger import setup_logger
from app.core.models import PolicyDocument, DocumentChunk


logger = setup_logger(__name__)


class DocumentProcessor:
    """Process and chunk policy documents."""
    
    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        logger.info(
            f"Initialized DocumentProcessor with chunk_size={chunk_size}, "
            f"chunk_overlap={chunk_overlap}"
        )
    
    def _generate_chunk_id(
        self,
        policy_id: str,
        chunk_index: int,
        content: str
    ) -> str:
        """Generate unique chunk ID."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{policy_id}_chunk_{chunk_index}_{content_hash}"
    
    def chunk_document(self, policy: PolicyDocument) -> List[DocumentChunk]:
        """
        Chunk a policy document into smaller pieces.
        
        Args:
            policy: PolicyDocument to chunk
        
        Returns:
            List of DocumentChunk objects
        """
        logger.info(f"Chunking document {policy.policy_id} ({policy.policy_domain})")
        
        # Split text into chunks
        text_chunks = self.text_splitter.split_text(policy.cleaned_content)
        
        # Create DocumentChunk objects
        chunks = []
        for idx, chunk_text in enumerate(text_chunks):
            chunk_id = self._generate_chunk_id(policy.policy_id, idx, chunk_text)
            
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                policy_id=policy.policy_id,
                policy_domain=policy.policy_domain,
                content=chunk_text,
                chunk_index=idx,
                source_url=policy.source_url,
                metadata={
                    "title": policy.title,
                    "scrape_timestamp": policy.scrape_timestamp.isoformat(),
                    "total_chunks": len(text_chunks),
                    **policy.metadata
                }
            )
            chunks.append(chunk)
        
        logger.info(
            f"Created {len(chunks)} chunks for document {policy.policy_id}"
        )
        return chunks
    
    def process_documents(
        self,
        policies: List[PolicyDocument]
    ) -> List[DocumentChunk]:
        """
        Process multiple policy documents.
        
        Args:
            policies: List of PolicyDocument objects
        
        Returns:
            List of all DocumentChunk objects
        """
        all_chunks = []
        
        for policy in policies:
            try:
                chunks = self.chunk_document(policy)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(
                    f"Failed to process document {policy.policy_id}: {str(e)}"
                )
        
        logger.info(
            f"Processed {len(policies)} documents into {len(all_chunks)} chunks"
        )
        return all_chunks
    
    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        """
        Save chunks to disk.
        
        Args:
            chunks: List of DocumentChunk objects
        """
        chunks_file = settings.CHUNKS_DIR / "chunks.json"
        
        # Convert to JSON-serializable format
        chunks_data = [
            {
                "chunk_id": chunk.chunk_id,
                "policy_id": chunk.policy_id,
                "policy_domain": chunk.policy_domain,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "source_url": chunk.source_url,
                "metadata": chunk.metadata,
                "created_at": chunk.created_at.isoformat()
            }
            for chunk in chunks
        ]
        
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2)
        
        logger.info(f"Saved {len(chunks)} chunks to {chunks_file}")
    
    def load_chunks(self) -> List[DocumentChunk]:
        """
        Load chunks from disk.
        
        Returns:
            List of DocumentChunk objects
        """
        chunks_file = settings.CHUNKS_DIR / "chunks.json"
        
        if not chunks_file.exists():
            logger.warning(f"Chunks file not found: {chunks_file}")
            return []
        
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        
        chunks = [
            DocumentChunk(
                chunk_id=data['chunk_id'],
                policy_id=data['policy_id'],
                policy_domain=data['policy_domain'],
                content=data['content'],
                chunk_index=data['chunk_index'],
                source_url=data['source_url'],
                metadata=data['metadata'],
                created_at=datetime.fromisoformat(data['created_at'])
            )
            for data in chunks_data
        ]
        
        logger.info(f"Loaded {len(chunks)} chunks from {chunks_file}")
        return chunks
    
    def get_chunks_by_domain(
        self,
        chunks: List[DocumentChunk],
        domain: str
    ) -> List[DocumentChunk]:
        """
        Filter chunks by policy domain.
        
        Args:
            chunks: List of all chunks
            domain: Policy domain to filter by
        
        Returns:
            Filtered list of chunks
        """
        filtered = [c for c in chunks if c.policy_domain == domain]
        logger.debug(f"Filtered {len(filtered)} chunks for domain '{domain}'")
        return filtered
    
    def get_statistics(self, chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """
        Get statistics about the chunks.
        
        Args:
            chunks: List of DocumentChunk objects
        
        Returns:
            Dictionary with statistics
        """
        if not chunks:
            return {}
        
        # Group by domain
        domain_counts = {}
        for chunk in chunks:
            domain = chunk.policy_domain
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Calculate content statistics
        content_lengths = [len(chunk.content) for chunk in chunks]
        
        stats = {
            "total_chunks": len(chunks),
            "domains": domain_counts,
            "avg_chunk_length": sum(content_lengths) / len(content_lengths),
            "min_chunk_length": min(content_lengths),
            "max_chunk_length": max(content_lengths),
            "unique_policies": len(set(c.policy_id for c in chunks))
        }
        
        return stats