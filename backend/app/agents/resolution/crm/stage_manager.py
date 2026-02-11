# stage_manager.py

PIPELINE_ID = "default"

STAGES = {
    "DELIVERED": "appointmentscheduled",
    "EXCHANGED": "qualifiedtobuy",
    "CANCELLED": "3071652573",
    "REFUND_DONE": "presentationscheduled"
}

def get_stage_transition(intent: str):
    """
    Decide CRM stage transitions based on intent.
    """
    intent = intent.lower()

    if intent == "exchange" or intent == "return":
        return ["EXCHANGED"]

    if intent == "cancel" or intent == "refund":
        # sequential transitions
        return ["CANCELLED", "REFUND_DONE"]

    return []

