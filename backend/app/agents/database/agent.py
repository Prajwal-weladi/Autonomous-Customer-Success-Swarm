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

    # 🔴 Case 1: No order ID extracted
    if not order_id:
        state["reply"] = "I could not find an order ID in your message. Please provide a valid order ID."
        state["status"] = "handoff"
        state["current_state"] = "HUMAN_HANDOFF"
        return state
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

    # 🟢 Case 2: Call real database
    db_response = fetch_order_details(order_id)

    # 🔴 Case 3: Order not found
    if not db_response.get("order_found"):
        state["reply"] = f"Order with ID {order_id} not found. Please verify your order ID."
        state["status"] = "completed"
        state["current_state"] = "COMPLETED"
        return state

    # 🟢 Case 4: Order found
    state["entities"]["order_details"] = db_response["order_details"]
    state["order_details"] = db_response["order_details"]

    # Move to next state
    state["current_state"] = "POLICY_CHECK"

    return state
