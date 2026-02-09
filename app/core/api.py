"""
FastAPI application for the Policy RAG Agent.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logger import setup_logger
from app.core.models import (
    QueryRequest,
    QueryResponse,
    ReindexRequest,
    ReindexResponse,
    HealthResponse
)
from app.core.model_enhanced import (
    PolicyQueryRequest,
    PolicyQueryResponse
)
from app.rag.service import rag_service
from app.rag.policy_evaluator import enhanced_policy_service


logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup
    logger.info("Starting Policy RAG Agent API...")
    try:
        rag_service.initialize()
        logger.info("RAG service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG service: {str(e)}")
        logger.warning("API started but RAG service is not available")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Policy RAG Agent API...")


# Create FastAPI app
app = FastAPI(
    title="Policy RAG Agent API",
    description="Advanced RAG pipeline for policy-based text generation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Policy RAG Agent API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/policy/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Check health status of the RAG service.
    
    Returns:
        Health status information
    """
    try:
        health = rag_service.get_health()
        return HealthResponse(**health)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@app.post("/policy/query", response_model=QueryResponse, tags=["Query"])
async def query_policy(request: QueryRequest) -> QueryResponse:
    """
    Query the policy knowledge base.
    
    Args:
        request: Query request with query text and optional conversation history
    
    Returns:
        Generated answer based on policy documents
    
    Raises:
        HTTPException: If query processing fails
    """
    try:
        logger.info(f"Received query: '{request.query}'")
        
        # Check if service is initialized
        if not rag_service._initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG service not initialized. Please check service health."
            )
        
        # Process query
        response = rag_service.query(request)
        
        logger.info("Query processed successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.post("/policy/evaluate", response_model=PolicyQueryResponse, tags=["Query"])
async def evaluate_policy_with_order(request: PolicyQueryRequest) -> PolicyQueryResponse:
    """
    Evaluate policy compliance with order context (NEW ENDPOINT).
    
    This endpoint accepts order details and returns structured evaluation
    of whether exchange/cancellation is allowed based on policy rules
    and order dates.
    
    Args:
        request: Query with order details (order_id, product, dates, status)
    
    Returns:
        Structured response with:
        - policy: Relevant policy text
        - exchange_allowed: Boolean
        - cancel_allowed: Boolean
        - reason: Detailed explanation
    
    Raises:
        HTTPException: If evaluation fails
    
    Example:
        POST /policy/evaluate
        {
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
        
        Response:
        {
            "policy": "Exchanges allowed within 7 days of delivery...",
            "exchange_allowed": false,
            "cancel_allowed": false,
            "reason": "Item delivered 15 days ago. Exchange period expired."
        }
    """
    try:
        logger.info(
            f"Received policy evaluation request for order {request.order_details.order_id}"
        )
        
        # Check if service is initialized
        if not rag_service._initialized:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG service not initialized. Please check service health."
            )
        
        # Evaluate policy with order context
        evaluation = enhanced_policy_service.query_with_order_context(
            query=request.query,
            order_details=request.order_details,
            conversation_history=request.conversation_history
        )
        
        logger.info(
            f"Policy evaluation complete: exchange={evaluation.exchange_allowed}, "
            f"cancel={evaluation.cancel_allowed}"
        )
        
        return PolicyQueryResponse(
            policy=evaluation.policy,
            exchange_allowed=evaluation.exchange_allowed,
            cancel_allowed=evaluation.cancel_allowed,
            reason=evaluation.reason
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Policy evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy evaluation failed: {str(e)}"
        )


@app.post("/policy/reindex", response_model=ReindexResponse, tags=["Management"])
async def reindex_policies(request: ReindexRequest) -> ReindexResponse:
    """
    Rebuild the policy document index.
    
    Args:
        request: Reindex request with optional force rescrape flag
    
    Returns:
        Reindexing statistics
    
    Raises:
        HTTPException: If reindexing fails
    """
    try:
        logger.info(f"Reindexing requested (force_rescrape={request.force_rescrape})")
        
        # Perform reindexing
        stats = rag_service.reindex(force_rescrape=request.force_rescrape)
        
        logger.info("Reindexing completed successfully")
        return ReindexResponse(**stats)
        
    except Exception as e:
        logger.error(f"Reindexing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindexing failed: {str(e)}"
        )


@app.get("/policy/statistics", tags=["Management"])
async def get_statistics() -> Dict[str, Any]:
    """
    Get detailed statistics about the RAG system.
    
    Returns:
        Statistics dictionary
    """
    try:
        stats = rag_service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.core.api:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )