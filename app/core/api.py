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
app = FastAPI()

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


@app.get("/policy/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    try:
        health = rag_service.get_health()
        return HealthResponse(**health)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


@app.post("/policy/query", response_model=QueryResponse)
async def query_policy(request: QueryRequest) -> QueryResponse:
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


@app.post("/policy/evaluate", response_model=PolicyQueryResponse)
async def evaluate_policy_with_order(request: PolicyQueryRequest) -> PolicyQueryResponse:
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


@app.post("/policy/reindex", response_model=ReindexResponse)
async def reindex_policies(request: ReindexRequest) -> ReindexResponse:
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


@app.get("/policy/statistics")
async def get_statistics() -> Dict[str, Any]:
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