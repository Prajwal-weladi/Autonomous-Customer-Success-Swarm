_STORE = {}

def load_state(conversation_id: str):
    return _STORE.get(conversation_id)

def save_state(conversation_id: str, state):
    _STORE[conversation_id] = state
