MAX_AGENT_CALLS = 2

def agent_guard(agent_name: str):
    def decorator(fn):
        async def wrapper(state):
            count = state["attempts"].get(agent_name, 0)

            if count >= MAX_AGENT_CALLS:
                state["current_state"] = "HUMAN_HANDOFF"
                state["status"] = "handoff"
                state["last_error"] = f"{agent_name} exceeded retry limit"
                return state

            state["attempts"][agent_name] = count + 1
            state["agents_called"].append(agent_name)

            return await fn(state)
        return wrapper
    return decorator
