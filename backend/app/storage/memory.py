"""
In-memory conversation state storage.
For production, replace with Redis, PostgreSQL, or other persistent storage.
"""

_STORE = {}


def load_state(conversation_id: str):
    """
    Load conversation state from storage.
    
    Args:
        conversation_id: Unique identifier for the conversation
        
    Returns:
        dict: Conversation state or None if not found
    """
    return _STORE.get(conversation_id)


def save_state(conversation_id: str, state):
    """
    Save conversation state to storage.
    
    Args:
        conversation_id: Unique identifier for the conversation
        state: Conversation state dict to save
    """
    _STORE[conversation_id] = state


def clear_state(conversation_id: str):
    """
    Clear conversation state from storage.
    
    Args:
        conversation_id: Unique identifier for the conversation
    """
    if conversation_id in _STORE:
        del _STORE[conversation_id]


def get_all_conversations():
    """
    Get all conversation IDs (for debugging).
    
    Returns:
        list: List of conversation IDs
    """
    return list(_STORE.keys())