from typing import TypedDict, Optional, List, Literal, Dict, Any

class ConversationState(TypedDict):
    conversation_id: str
    current_state: Literal[
        "AWAITING_INTENT",
        "DATA_FETCH",
        "POLICY_CHECK",
        "RESOLUTION",
        "COMPLETED",
        "HUMAN_HANDOFF"
    ]
    user_message: Optional[str]

    intent: Optional[str]
    urgency: Optional[str]
    entities: Dict[str, Any]

    agents_called: List[str]
    attempts: Dict[str, int]
    last_error: Optional[str]

    reply: Optional[str]
    status: Literal["in_progress", "completed", "handoff"]