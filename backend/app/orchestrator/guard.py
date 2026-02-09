MAX_AGENT_CALLS = 2

def agent_guard(agent_name: str):
    """
    Decorator to guard agents from infinite loops.
    Limits the number of times an agent can be called.
    """
    def decorator(fn):
        async def wrapper(state):
            # Initialize attempts dict if not exists
            if "attempts" not in state:
                state["attempts"] = {}
            
            # Get current attempt count
            count = state["attempts"].get(agent_name, 0)

            # Check if limit exceeded
            if count >= MAX_AGENT_CALLS:
                state["current_state"] = "HUMAN_HANDOFF"
                state["status"] = "handoff"
                state["last_error"] = f"{agent_name} exceeded retry limit ({MAX_AGENT_CALLS} attempts)"
                return state

            # Increment counter and track call
            state["attempts"][agent_name] = count + 1
            
            # Initialize agents_called list if not exists
            if "agents_called" not in state:
                state["agents_called"] = []
            
            state["agents_called"].append(agent_name)

            try:
                # Execute the actual agent function
                return await fn(state)
            except Exception as e:
                # Catch any errors and mark for escalation
                state["last_error"] = f"{agent_name} error: {str(e)}"
                state["current_state"] = "HUMAN_HANDOFF"
                state["status"] = "handoff"
                return state
                
        return wrapper
    return decorator