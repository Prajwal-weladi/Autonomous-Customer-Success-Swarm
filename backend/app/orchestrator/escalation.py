def should_escalate(state) -> bool:
    """
    Determines if the conversation should be escalated to a human agent.
    
    Escalation triggers:
    1. Any error occurred in the last step
    2. Total attempts across all agents exceed threshold
    3. Current state is already HUMAN_HANDOFF
    """
    # Check if already in handoff state
    if state.get("current_state") == "HUMAN_HANDOFF":
        return True
    
    # Check if there was an error
    if state.get("last_error"):
        return True

    # Check total attempts across all agents
    total_attempts = sum(state.get("attempts", {}).values())
    if total_attempts > 5:
        return True

    return False