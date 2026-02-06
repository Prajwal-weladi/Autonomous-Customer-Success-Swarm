from app.orchestrator.guard import agent_guard

@agent_guard("policy")
async def policy_agent(state):
    state["entities"]["refund_allowed"] = True
    state["current_state"] = "RESOLUTION"
    return state
