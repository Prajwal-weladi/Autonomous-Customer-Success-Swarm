from app.orchestrator.graph import build_graph
from app.storage.memory import load_state, save_state
from app.orchestrator.escalation import should_escalate
from app.utils.logger import get_logger

logger = get_logger(__name__)

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
    logger.info(f"🚀 ORCHESTRATOR STARTED | Conversation: {conversation_id}")
    logger.debug(f"User message: '{message}'")
    
    state = load_state(conversation_id)

    if not state:
        logger.info(f"📝 Initializing new conversation state for {conversation_id}")
        # Initialize new conversation state
        state = {
            "conversation_id": conversation_id,
            "current_state": "AWAITING_INTENT",
            "user_message": message,
            "intent": None,
            "urgency": None,
            "entities": {},
            "order_details": None,
            "agents_called": [],
            "attempts": {},
            "last_error": None,
            "reply": None,
            "amount": None,
            "status": "in_progress",
            "awaiting_order_id": False,
            "awaiting_confirmation": False,
            "pending_action": None
        }
    else:
        logger.info(f"🔄 Loading existing conversation state for {conversation_id}")
        logger.debug(f"Previous state: {state.get('current_state')}, Intent: {state.get('intent')}")
        # Update existing conversation with new message
        state["user_message"] = message
        state["status"] = "in_progress"
        state["last_error"] = None  # Reset error for new message

    try:
        logger.info("⚙️ Invoking agent workflow graph")
        # Run the graph workflow
        result = await graph.ainvoke(state)
        
        logger.info(f"✅ Graph execution completed | Final state: {result.get('current_state')}")
        logger.debug(f"Intent: {result.get('intent')}, Status: {result.get('status')}")

        # Check if escalation is needed
        if should_escalate(result):
            logger.warning(f"🚨 Escalation triggered for conversation {conversation_id}")
            result["status"] = "handoff"
            result["current_state"] = "HUMAN_HANDOFF"
            if not result.get("reply"):
                result["reply"] = "I apologize, but I need to escalate this to a human agent for better assistance. Someone will get back to you shortly."

        # Save the final state
        logger.info(f"💾 Saving final state for {conversation_id}")
        save_state(conversation_id, result)
        
        logger.info(f"🏁 ORCHESTRATOR COMPLETED | Status: {result.get('status')}")
        return result
        
    except Exception as e:
        logger.error(f"❌ ORCHESTRATOR ERROR: {str(e)}", exc_info=True)
        # Handle any unexpected errors
        state["last_error"] = f"Orchestrator error: {str(e)}"
        state["status"] = "handoff"
        state["current_state"] = "HUMAN_HANDOFF"
        state["reply"] = "I apologize, but I encountered an error. Let me connect you with a human agent."
        save_state(conversation_id, state)
        return state