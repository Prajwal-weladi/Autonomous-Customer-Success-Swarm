from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.orchestrator.runner import run_orchestrator

router = APIRouter()


class MessageRequest(BaseModel):
    conversation_id: str
    message: str


class MessageResponse(BaseModel):
    conversation_id: str
    reply: Optional[str]
    status: str
    intent: Optional[str] = None
    urgency: Optional[str] = None
    order_id: Optional[str] = None
    user_issue: Optional[str] = None
    triage_confidence: Optional[float] = None
    order_details: Optional[Dict[str, Any]] = None
    agents_called: Optional[list] = None
    current_state: Optional[str] = None


@router.post("/v1/message", response_model=MessageResponse, response_model_exclude_none=True)
async def handle_message(req: MessageRequest):
    """
    Main endpoint for handling customer messages.
    
    Args:
        req: MessageRequest containing conversation_id and message
        
    Returns:
        MessageResponse with the agent's reply and metadata
    """
    try:
        # Run the orchestrator
        state = await run_orchestrator(
            req.conversation_id,
            req.message
        )

        # Build response
        return MessageResponse(
            conversation_id=state["conversation_id"],
            reply=None,
            status=state["status"],
            intent=state.get("intent"),
            urgency=state.get("urgency"),
            order_id=state.get("entities", {}).get("order_id"),
            user_issue=state.get("entities", {}).get("user_issue"),
            triage_confidence=state.get("entities", {}).get("triage_confidence"),
            order_details=state.get("entities", {}).get("order_details"),
            agents_called=state.get("agents_called"),
            current_state=state.get("current_state")
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "customer_success_orchestrator"}