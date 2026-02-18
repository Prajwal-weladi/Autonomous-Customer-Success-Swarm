# stage_manager.py

PIPELINE_ID = "default"

STAGES = {
    "DELIVERED": "appointmentscheduled",
    "EXCHANGED": "qualifiedtobuy",
    "CANCELLED": "3071652573",
    "REFUND_DONE": "presentationscheduled",
    "RETURNED": "3171778267"
}

def get_stage_transition(intent: str):
    """
    Decide CRM stage transitions based on intent.
    """
    intent = intent.lower()

    if intent == "exchange":
        return ["EXCHANGED"]

    if intent == "cancel" or intent == "refund":
        # sequential transitions
        return ["CANCELLED", "REFUND_DONE"]

    if intent == "return":
        return ["RETURNED"]

    return []

