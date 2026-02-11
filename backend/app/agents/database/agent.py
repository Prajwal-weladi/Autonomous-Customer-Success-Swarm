from app.orchestrator.guard import agent_guard
from app.agents.database.db_service import fetch_order_details


@agent_guard("database")
async def database_agent(state):
    """
    Database Agent: Fetches order details from the database using Text-to-SQL.
    
    Expects:
        - state["entities"]["order_id"] to be set by triage agent
        
    Sets:
        - state["entities"]["order_details"] with fetched data
        - state["current_state"] to "POLICY_CHECK" on success
        - state["current_state"] to "HUMAN_HANDOFF" on error
    """
    # Ensure entities exist and fetch order_id (set by triage)
    state.setdefault("entities", {})
    order_id = state["entities"].get("order_id")

    if not order_id:
        # Check intent - some intents don't require order_id
        intent = state.get("intent")
        
        if intent in ["general_question", "technical_issue"]:
            # For these intents, we can skip database lookup
            state["entities"]["order_details"] = None
            state["order_details"] = None
            state["current_state"] = "POLICY_CHECK"
            return state
        else:
            # For order-specific intents, order_id is required
            state["last_error"] = "Order ID not found - cannot fetch order details"
            state["current_state"] = "HUMAN_HANDOFF"
            return state

    # Fetch order details from database
    db_response = fetch_order_details(order_id)

    if not db_response.get("order_found"):
        # Order not found in database
        error_msg = db_response.get("error", "Order not found")
        state["last_error"] = f"Database lookup failed: {error_msg}"
        state["current_state"] = "HUMAN_HANDOFF"
        return state

    # Successfully fetched order details
    state["entities"]["order_details"] = db_response["order_details"]
    state["order_details"] = db_response["order_details"]

    # Move to next state
    state["current_state"] = "POLICY_CHECK"
    return state