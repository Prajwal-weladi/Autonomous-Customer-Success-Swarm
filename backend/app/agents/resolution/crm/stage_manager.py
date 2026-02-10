# stage_manager.py

PIPELINE_ID = "default"

STAGES = {
    "DELIVERED": "appointmentscheduled",
    "EXCHANGED": "qualifiedtobuy",
    "CANCELLED": "cancelled",
    "REFUND_DONE": "refund_done"
}

def get_stage_transition(intent: str):
    """
    Decide CRM stage transitions based on intent.
    """
    intent = intent.lower()

    if intent == "exchange":
        return ["EXCHANGED"]

    if intent == "cancel":
        # sequential transitions
        return ["CANCELLED", "REFUND_DONE"]

    return []
