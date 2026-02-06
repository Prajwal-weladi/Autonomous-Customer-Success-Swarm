from app.orchestrator.guard import agent_guard
from app.agents.database.db_service import fetch_order_details

@agent_guard("database")
async def database_agent(state):
    # 1️⃣ Get order_id from state (set by triage)
    order_id = state["entities"].get("order_id")

    if not order_id:
        state["last_error"] = "Order ID not found in state"
        state["current_state"] = "HANDOFF"
        return state

    # 2️⃣ Call REAL database logic
    db_response = fetch_order_details(order_id)

    if not db_response.get("order_found"):
        state["last_error"] = "Order not found"
        state["current_state"] = "HANDOFF"
        return state

    # 3️⃣ Store order details in shared state
    state["entities"]["order_details"] = db_response["order_details"]

    # 4️⃣ Move to next step
    state["current_state"] = "POLICY_CHECK"
    return state
