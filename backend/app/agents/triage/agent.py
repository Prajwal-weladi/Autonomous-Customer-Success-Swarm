from app.orchestrator.guard import agent_guard

@agent_guard("triage")
async def triage_agent(state):
    state["intent"] = "refund"
    state["urgency"] = "high"
    state["current_state"] = "DATA_FETCH"
    return state
