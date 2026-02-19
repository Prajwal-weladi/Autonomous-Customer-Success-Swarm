"""
In-memory conversation state storage.
For production, replace with Redis, PostgreSQL, or other persistent storage.
"""
from app.utils.logger import get_logger

logger = get_logger(__name__)

_STORE = {}
_HISTORY: dict[str, list[dict]] = {}  # conversation_id -> [{role, content}, ...]


def load_state(conversation_id: str):
    """
    Load conversation state from storage.
    
    Args:
        conversation_id: Unique identifier for the conversation
        
    Returns:
        dict: Conversation state or None if not found
    """
    logger.debug(f"📂 MEMORY: Loading state for conversation {conversation_id}")
    state = _STORE.get(conversation_id)
    if state:
        logger.info(f"✅ MEMORY: State found for {conversation_id}")
    else:
        logger.info(f"ℹ️ MEMORY: No existing state for {conversation_id}")
    return state


def save_state(conversation_id: str, state):
    """
    Save conversation state to storage.
    
    Args:
        conversation_id: Unique identifier for the conversation
        state: Conversation state dict to save
    """
    logger.debug(f"💾 MEMORY: Saving state for conversation {conversation_id}")
    _STORE[conversation_id] = state
    logger.info(f"✅ MEMORY: State saved for {conversation_id}")


def clear_state(conversation_id: str):
    """
    Clear conversation state from storage.
    
    Args:
        conversation_id: Unique identifier for the conversation
    """
    logger.debug(f"🗑️ MEMORY: Clearing state for conversation {conversation_id}")
    if conversation_id in _STORE:
        del _STORE[conversation_id]
        logger.info(f"✅ MEMORY: State cleared for {conversation_id}")
    else:
        logger.warning(f"⚠️ MEMORY: No state to clear for {conversation_id}")


def get_all_conversations():
    """
    Get all conversation IDs (for debugging).
    
    Returns:
        list: List of conversation IDs
    """
    conversations = list(_STORE.keys())
    logger.debug(f"📋 MEMORY: {len(conversations)} conversations in storage")
    return conversations


def get_history(conversation_id: str) -> list[dict]:
    """
    Return the message history for a conversation.

    Returns:
        list of dicts with 'role' ('user' | 'assistant') and 'content' keys.
    """
    return _HISTORY.get(conversation_id, [])


def append_to_history(conversation_id: str, role: str, content: str, max_turns: int = 20):
    """
    Append a single turn to the conversation history.
    Caps the stored history at *max_turns* messages (oldest dropped first).

    Args:
        conversation_id: Unique identifier for the conversation
        role: 'user' or 'assistant'
        content: The message text
        max_turns: Maximum number of messages to retain (default 20)
    """
    if conversation_id not in _HISTORY:
        _HISTORY[conversation_id] = []
    _HISTORY[conversation_id].append({"role": role, "content": content})
    # Trim to avoid unbounded growth
    if len(_HISTORY[conversation_id]) > max_turns:
        _HISTORY[conversation_id] = _HISTORY[conversation_id][-max_turns:]
    logger.debug(f"📝 MEMORY: History updated for {conversation_id} ({len(_HISTORY[conversation_id])} turns)")