from app.orchestrator.guard import agent_guard

@agent_guard("resolution")
async def resolution_agent(state):
    state["reply"] = "Your refund has been initiated successfully."
    state["status"] = "completed"
    state["current_state"] = "COMPLETED"
    return state
