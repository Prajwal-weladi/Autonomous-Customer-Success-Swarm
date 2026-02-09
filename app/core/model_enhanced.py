"""
Enhanced data models for order-based policy evaluation.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OrderDetails(BaseModel):
    """Order details from database agent."""
    
    order_id: int
    product: str
    size: Optional[int] = None
    order_date: str  # Format: "YYYY-MM-DD"
    delivered_date: Optional[str] = None  # Format: "YYYY-MM-DD" or "None"
    status: str  # e.g., "Shipped", "Delivered", "Processing"


class PolicyQueryInput(BaseModel):
    """Input model for policy evaluation with order context."""
    
    query: str = Field(..., min_length=3, description="User query text")
    order_details: OrderDetails = Field(..., description="Order information from database")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Can I exchange this item?",
                "order_details": {
                    "order_id": 7847,
                    "product": "Puma Jacket",
                    "size": 40,
                    "order_date": "2026-01-20",
                    "delivered_date": "2026-01-25",
                    "status": "Delivered"
                },
                "conversation_history": []
            }
        }


class PolicyEvaluationOutput(BaseModel):
    """Structured output for policy evaluation."""
    
    policy: str = Field(..., description="Relevant policy text or summary")
    exchange_allowed: bool = Field(..., description="Whether exchange is allowed")
    cancel_allowed: bool = Field(..., description="Whether cancellation is allowed")
    reason: str = Field(..., description="Explanation for the decision")
    
    class Config:
        json_schema_extra = {
            "example": {
                "policy": "Returns and exchanges are allowed within 7 days of delivery for unused items in original packaging.",
                "exchange_allowed": False,
                "cancel_allowed": False,
                "reason": "The delivery was made 15 days ago (delivered on 2026-01-25). Our policy allows exchanges only within 7 days of delivery. The exchange period expired on 2026-02-01."
            }
        }


class PolicyQueryRequest(BaseModel):
    """API request model for policy queries with order context."""
    
    query: str = Field(..., min_length=3, description="User query text")
    order_details: OrderDetails = Field(..., description="Order information")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "I want to return this jacket",
                "order_details": {
                    "order_id": 7847,
                    "product": "Puma Jacket",
                    "size": 40,
                    "order_date": "2026-01-20",
                    "delivered_date": "2026-01-25",
                    "status": "Delivered"
                },
                "conversation_history": []
            }
        }


class PolicyQueryResponse(BaseModel):
    """API response model for policy evaluation."""
    
    policy: str
    exchange_allowed: bool
    cancel_allowed: bool
    reason: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "policy": "Exchanges allowed within 7 days of delivery",
                "exchange_allowed": True,
                "cancel_allowed": False,
                "reason": "Item was delivered 3 days ago. Exchange is allowed within the 7-day window. Cancellation is not possible as the order has been delivered."
            }
        }


# Keep backward compatibility with old models
class QueryRequest(BaseModel):
    """Legacy API request model for simple queries."""
    
    query: str = Field(..., min_length=3, description="User query text")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
    filter_domain: Optional[str] = Field(
        None,
        description="Optional domain filter"
    )


class QueryResponse(BaseModel):
    """Legacy API response model."""
    
    answer: str = Field(..., description="Generated answer text only")


# Other existing models remain unchanged
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