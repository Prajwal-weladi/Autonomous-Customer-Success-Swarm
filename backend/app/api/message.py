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

@router.post("/v1/message", response_model=MessageResponse)
async def handle_message(req: MessageRequest):
    state = await run_orchestrator(
        req.conversation_id,
        req.message
    )

    return {
        "conversation_id": state["conversation_id"],
        "reply": state.get("reply"),
        "status": state["status"]
    }
