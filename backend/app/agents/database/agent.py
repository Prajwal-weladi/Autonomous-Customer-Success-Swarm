from app.orchestrator.guard import agent_guard

@agent_guard("database")
async def database_agent(state):
    state["entities"]["order_status"] = "DELIVERED"
    state["current_state"] = "POLICY_CHECK"
    return state
