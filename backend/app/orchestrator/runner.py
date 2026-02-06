from app.orchestrator.graph import build_graph
from app.storage.memory import load_state, save_state
from app.orchestrator.escalation import should_escalate

graph = build_graph()

async def run_orchestrator(conversation_id: str, message: str):
    state = load_state(conversation_id)

    if not state:
        state = {
            "conversation_id": conversation_id,
            "current_state": "AWAITING_INTENT",
            "user_message": message,
            "intent": None,
            "urgency": None,
            "entities": {},
            "agents_called": [],
            "attempts": {},
            "last_error": None,
            "reply": None,
            "status": "in_progress"
        }
    else:
        state["user_message"] = message

    result = await graph.ainvoke(state)

    if should_escalate(result):
        result["status"] = "handoff"
        result["current_state"] = "HUMAN_HANDOFF"

    save_state(conversation_id, result)
    return result
