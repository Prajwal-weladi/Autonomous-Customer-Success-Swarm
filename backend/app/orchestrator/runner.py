from app.orchestrator.graph import build_graph
from app.storage.memory import load_state, save_state
from app.orchestrator.escalation import should_escalate

graph = build_graph()

async def run_orchestrator(conversation_id: str, message: str):
    """
    Main orchestrator function that runs the agent workflow.
    
    Args:
        conversation_id: Unique identifier for the conversation
        message: User's message
        
    Returns:
        Final state after processing through all agents
    """
    state = load_state(conversation_id)

    if not state:
        # Initialize new conversation state
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
        # Update existing conversation with new message
        state["user_message"] = message
        state["status"] = "in_progress"
        state["last_error"] = None  # Reset error for new message

    try:
        # Run the graph workflow
        result = await graph.ainvoke(state)

        # Check if escalation is needed
        if should_escalate(result):
            result["status"] = "handoff"
            result["current_state"] = "HUMAN_HANDOFF"
            if not result.get("reply"):
                result["reply"] = "I apologize, but I need to escalate this to a human agent for better assistance. Someone will get back to you shortly."

        # Save the final state
        save_state(conversation_id, result)
        return result
        
    except Exception as e:
        # Handle any unexpected errors
        state["last_error"] = f"Orchestrator error: {str(e)}"
        state["status"] = "handoff"
        state["current_state"] = "HUMAN_HANDOFF"
        state["reply"] = "I apologize, but I encountered an error. Let me connect you with a human agent."
        save_state(conversation_id, state)
        return state