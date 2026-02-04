def should_escalate(state) -> bool:
    if state["last_error"]:
        return True

    total_attempts = sum(state["attempts"].values())
    if total_attempts > 5:
        return True

    return False
