from app.agents.resolution.core.services.return_label_service import generate_return_label
from app.agents.resolution.app.schemas.model import ResolutionInput


def run_agent_llm(data: ResolutionInput) -> dict:
    """
    Resolution Agent using deterministic business logic.
    Handles exchange, cancel, refund, order tracking,
    complaints, and technical issues.
    """

    intent = data.intent.lower()

    # ----------------- DIRECT INTENTS -----------------

    # 1️⃣ Order Tracking
    if intent == "order_tracking":
        return {
            "action": "order_tracking",
            "message": f"Order {data.order_id} is currently {data.status}.",
            "order_id": data.order_id,
            "status": data.status,
            "return_label_url": None,
            "refund_amount": None,
            "reason": None
        }

    # 2️⃣ Complaint
    if intent == "complaint":
        return {
            "action": "complaint",
            "message": f"Your complaint for order {data.order_id} has been registered and will be resolved shortly.",
            "order_id": data.order_id,
            "reason": getattr(data, "reason", None),
            "return_label_url": None,
            "refund_amount": None
        }

    # 3️⃣ Technical Issue
    if intent == "technical_issue":
        return {
            "action": "technical_issue",
            "message": f"We have received your technical issue for order {data.order_id}. Our technical team will resolve it soon.",
            "order_id": data.order_id,
            "reason": getattr(data, "reason", None),
            "return_label_url": None,
            "refund_amount": None
        }

    # ----------------- BUSINESS RULE CHECKS -----------------

    # Cancel/Refund not allowed
    if intent in ["cancel", "refund"] and not data.cancel_allowed:
        return {
            "action": "deny",
            "message": f"Cancellation not allowed for order {data.order_id}.",
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    # Exchange/Return not allowed
    if intent in ["exchange", "return"] and not data.exchange_allowed:
        return {
            "action": "deny",
            "message": f"Exchange not allowed for order {data.order_id}.",
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    # ----------------- MAIN ACTION LOGIC -----------------

    # Exchange / Return
    if intent in ["exchange", "return"] and data.exchange_allowed:
        file_name = generate_return_label(
            data.order_id,
            product=data.product,
            size=data.size
        )
        return {
            "action": "exchange",
            "message": f"Exchange processed for order {data.order_id}.",
            "return_label_url": f"http://localhost:8000/labels/{file_name}",
            "refund_amount": None,
            "reason": None
        }

    # Cancel / Refund
    if intent in ["cancel", "refund"] and data.cancel_allowed:
        return {
            "action": "cancel",
            "message": f"Order {data.order_id} cancelled. Refund of ₹{data.amount} processed.",
            "return_label_url": None,
            "refund_amount": data.amount,
            "reason": None
        }

    # ----------------- DEFAULT FALLBACK -----------------

    return {
        "action": "deny",
        "message": f"{intent.capitalize()} cannot be processed for order {data.order_id}.",
        "return_label_url": None,
        "refund_amount": None,
        "reason": getattr(data, "reason", None)
    }


