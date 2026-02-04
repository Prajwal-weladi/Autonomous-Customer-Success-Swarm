"""
Data models for the Policy RAG Agent.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class PolicyDocument(BaseModel):
    """Raw policy document model."""
    
    policy_id: str
    policy_domain: str
    title: str
    source_url: str
    raw_content: str
    cleaned_content: str
    scrape_timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Chunked document with metadata."""
    
    chunk_id: str
    policy_id: str
    policy_domain: str
    content: str
    chunk_index: int
    source_url: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QueryRequest(BaseModel):
    """API request model for policy queries."""
    
    query: str = Field(..., min_length=3, description="User query text")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
    filter_domain: Optional[str] = Field(
        None,
        description="Optional domain filter"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "",
                "conversation_history": [],
                "filter_domain": ""
            }
        }


class QueryResponse(BaseModel):
    """API response model for policy queries."""
    
    answer: str = Field(..., description="Generated answer text only")
    
    class Config:
        json_schema_extra = {
            "example": {
                "answer": ""
            }
        }


class ReindexRequest(BaseModel):
    """Request model for reindexing operation."""
    
    force_rescrape: bool = Field(
        default=False,
        description="Whether to force rescraping of policies"
    )


class ReindexResponse(BaseModel):
    """Response model for reindexing operation."""
    
    status: str
    documents_processed: int
    chunks_created: int
    embeddings_generated: int
    duration_seconds: float


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    version: str
    ollama_connected: bool
    index_loaded: bool
    documents_indexed: int


class RetrievedContext(BaseModel):
    """Internal model for retrieved context."""
    
    content: str
    policy_domain: str
    source_url: str
    relevance_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TranslatedQuery(BaseModel):
    """Model for translated/optimized query."""
    
    original_query: str
    translated_query: str
    reasoning: str


class QueryRoute(BaseModel):
    """Model for query routing decision."""
    
    selected_domain: str
    confidence: float
    reasoning: str