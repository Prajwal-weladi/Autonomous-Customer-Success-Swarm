from fastapi import APIRouter
from pydantic import BaseModel
from app.orchestrator.runner import run_orchestrator

router = APIRouter()

class MessageRequest(BaseModel):
    conversation_id: str
    message: str

class MessageResponse(BaseModel):
    conversation_id: str
    reply: str | None
    status: str
    intent: str | None = None
    urgency: str | None = None
    order_id: str | None = None
    triage_confidence: float | None = None

@router.post("/v1/message", response_model=MessageResponse)
async def handle_message(req: MessageRequest):
    state = await run_orchestrator(
        req.conversation_id,
        req.message
    )

    return {
        "conversation_id": state["conversation_id"],
        "reply": state.get("reply"),
        "status": state["status"],
        "intent": state.get("intent"),
        "urgency": state.get("urgency"),
        "order_id": state.get("entities", {}).get("order_id"),
        "triage_confidence": state.get("entities", {}).get("triage_confidence"),
    }
