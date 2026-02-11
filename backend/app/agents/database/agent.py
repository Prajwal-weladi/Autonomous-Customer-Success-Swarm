from app.orchestrator.guard import agent_guard
from app.agents.database.db_service import fetch_order_details


@agent_guard("database")
async def database_agent(state):

    order_id = state["entities"].get("order_id")

    # 🔴 Case 1: No order ID extracted
    if not order_id:
        state["reply"] = "I could not find an order ID in your message. Please provide a valid order ID."
        state["status"] = "handoff"
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
    state["current_state"] = "POLICY_CHECK"

    return state
