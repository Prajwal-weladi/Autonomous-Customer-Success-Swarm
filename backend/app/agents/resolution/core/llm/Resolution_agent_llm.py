from ollama import chat
import json
from ...core.llm.prompt import get_llm_prompt
from ...core.services.return_label_service import generate_return_label
from app.agents.resolution.app.schemas.model import ResolutionInput


def run_agent_llm(data: ResolutionInput) -> dict:
    """
    Resolution Agent using deterministic business logic.
    Handles exchange, cancel, refund, order tracking,
    complaints, and technical issues.
    """

    intent = (data.intent or "").lower()

    # ✅ SAFE FALLBACKS (VERY IMPORTANT)
    product_name = data.product or "the product"
    size_value = data.size if data.size not in [None, 0, "0"] else "N/A"
    order_status = getattr(data, "status", "processing")

    # ----------------- DIRECT INTENTS -----------------

    # 1️⃣ Order Tracking
    if intent == "order_tracking":
        return {
            "action": "order_tracking",
            "message": (
                f"📦 Order Update\n\n"
                f"Your order **#{data.order_id}** is currently **{order_status}**.\n"
                f"If you need further help, I'm here for you!"
            ),
            "order_id": data.order_id,
            "status": order_status,
            "return_label_url": None,
            "refund_amount": None,
            "reason": None
        }

    # 2️⃣ Complaint
    if intent == "complaint":
        return {
            "action": "complaint",
            "message": (
                f"🙏 We're sorry for the inconvenience.\n\n"
                f"Your complaint for order **#{data.order_id}** has been registered.\n"
                f"Our support team will review and get back to you shortly."
            ),
            "order_id": data.order_id,
            "reason": getattr(data, "reason", None),
            "return_label_url": None,
            "refund_amount": None
        }

    # 3️⃣ Technical Issue
    if intent == "technical_issue":
        return {
            "action": "technical_issue",
            "message": (
                f"🛠️ Technical Issue Logged\n\n"
                f"We've received your issue for order **#{data.order_id}**.\n"
                f"Our technical team will investigate and update you soon."
            ),
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
            "message": (
                f"❌ Refund/Cancellation Not Allowed\n\n"
                f"Order **#{data.order_id}** is not eligible.\n"
                f"Reason: {data.reason}"
            ),
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    # Exchange/Return not allowed
    if intent in ["exchange", "return"] and not data.exchange_allowed:
        return {
            "action": "deny",
            "message": (
                f"❌ Exchange Not Allowed\n\n"
                f"Order **#{data.order_id}** is not eligible.\n"
                f"Reason: {data.reason}"
            ),
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    # ----------------- MAIN ACTION LOGIC -----------------

    # Exchange / Return
    if intent in ["exchange", "return"] and data.exchange_allowed:
        file_name = generate_return_label(
            data.order_id,
            product=product_name,
            size=data.size
        )

        return {
            "action": "exchange",
            "message": (
                f"✅ Your exchange request has been approved!\n\n"
                f"📦 Product: {product_name}\n"
                f"🔢 Order ID: {data.order_id}\n"
                f"📏 Size: {size_value}\n\n"
                f"📄 A prepaid return label has been generated.\n"
                f"Please print the label, attach it to your package,\n"
                f"and ship it back using any courier service.\n\n"
                f"🔁 Once we receive the item, your replacement will be processed."
            ),
            "return_label_url": f"http://localhost:8000/labels/{file_name}",
            "refund_amount": None,
            "reason": None
        }

    # Cancel / Refund
    if intent in ["cancel", "refund"] and data.cancel_allowed:
        return {
            "action": "cancel",
            "message": (
                f"💰 Refund Initiated\n\n"
                f"Your order **#{data.order_id}** has been cancelled.\n"
                f"Refund of **₹{data.amount}** will be processed shortly."
            ),
            "return_label_url": None,
            "refund_amount": data.amount,
            "reason": None
        }

    # ----------------- DEFAULT FALLBACK -----------------

    return {
        "action": "deny",
        "message": (
            f"⚠️ Unable to process request\n\n"
            f"{intent.capitalize()} cannot be completed for order **#{data.order_id}**."
        ),
        "return_label_url": None,
        "refund_amount": None,
        "reason": getattr(data, "reason", None)
    }
