

# prompt.py

from ...app.schemas.model import ResolutionInput


def get_llm_prompt(data: ResolutionInput) -> str:
    """
    Generate LLM prompt dynamically based on input JSON.
    Handles exchange, cancel (with implied refund), and other intents.
    Includes denial reason in the output JSON when exchange or cancel is not allowed.
    """

    prompt = f"""
You are a Resolution Agent. Make a decision and generate output JSON for the following order:

Order ID: {data.order_id}
Intent: {data.intent}
Product: {data.product}
Size: {data.size}
Amount: {data.amount}
"""

    # Handle exchange
    if data.intent.lower() == "exchange":
        prompt += f"Exchange Allowed: {data.exchange_allowed}\n"
        if data.exchange_allowed:
            prompt += "If exchange is allowed, generate a return label URL in format https://http://localhost:8000/labels/{data.order_id}.pdf\n"
        else:
            prompt += f"Exchange is denied. Reason: {data.reason}\n"

    # Handle cancel intent
    elif data.intent.lower() == "cancel":
        prompt += f"Cancel Allowed: {data.cancel_allowed}\n"
        if data.cancel_allowed:
            prompt += f"Refund Allowed: true\n"
            prompt += f"Refund Amount: {data.amount}\n"
            prompt += "Generate proper message and JSON with refund_amount and status updates.\n"
        else:
            prompt += f"Refund Allowed: false\n"
            prompt += f"Cancellation denied. Reason: {data.reason}\n"

    # Handle any other unknown or random intents
    else:
        prompt += "For any other or unknown intent, generate an appropriate action.\n"
        prompt += "You can suggest gift vouchers, alternative offers, or proper message to user.\n"

    # Output format instruction including reason
    prompt += """
Output JSON ONLY in the format:

{
    "action": "<exchange allowed /refund & cancel allowed /exchange denied/refund & cancel allowed denied/other>",
    "message": "<Message for the user>",
    "return_label_url": "<if exchange, optional>",
    "refund_amount": "<if refund, optional>",
    "reason": "<if action is denied, include reason here>"
}
Do NOT include any explanation, comments or extra text.
"""
    return prompt
