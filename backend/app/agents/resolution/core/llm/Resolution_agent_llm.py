from ollama import chat
import json
from ...core.llm.prompt import get_llm_prompt
from ...core.services.return_label_service import generate_return_label
from app.agents.resolution.app.schemas.model import ResolutionInput


def run_agent_llm(data: ResolutionInput) -> dict:
    """
    Run the Resolution Agent using LLM for exchange/cancel/refund actions.
    Handles business rules and generates return labels for exchanges.
    """

    # ----------------- Business Rule Check -----------------
    # Cancel intent implies refund
    if data.intent.lower() == "cancel" or data.intent.lower() == "refund"and data.cancel_allowed is False:
        return {
            "action": "deny",
            "message": f"Cancellation not allowed for order {data.order_id}.",
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    # Exchange not allowed
    if data.intent.lower() == "exchange" and data.exchange_allowed is False:
        return {
            "action": "deny",
            "message": f"Exchange not allowed for order {data.order_id}.",
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    # ----------------- LLM Call -----------------
    prompt_text = get_llm_prompt(data)

    try:
        response = chat(model="llama3", messages=[{"role": "user", "content": prompt_text}])
        output = json.loads(response['content'])
    except Exception:
        # Fallback if LLM fails
        if data.intent.lower() == "exchange" and data.exchange_allowed:
            file_name = generate_return_label(data.order_id)
            return {
                "action": "exchange",
                "message": f"Exchange processed for order {data.order_id}.",
                "return_label_url": f"http://localhost:8000/labels/{file_name}",
                "refund_amount": None,
                "reason": None
            }

        elif data.intent.lower() == "cancel" or data.intent.lower() == "refund" and data.cancel_allowed:
            return {
                "action": "cancel",
                "message": f"Order {data.order_id} cancelled. Refund of ₹{data.amount} processed.",
                "return_label_url": None,
                "refund_amount": data.amount,
                "reason": None
            }

        else:
            # Denied fallback
            return {
                "action": "deny",
                "message": f"{data.intent.capitalize()} cannot be processed for order {data.order_id}.",
                "return_label_url": None,
                "refund_amount": None,
                "reason": data.reason
            }

    # ----------------- Handle Exchange PDF -----------------
    if output.get("action") == "exchange" and data.exchange_allowed:
        file_name = generate_return_label(data.order_id, product=data.product, size=data.size)
        output["return_label_url"] = f"http://localhost:8000/labels/{file_name}"

    # Ensure denial reasons are included
    if output.get("action") == "deny" and "reason" not in output:
        output["reason"] = data.reason

    return output


