from ...core.services.return_label_service import generate_return_label
from app.agents.resolution.app.schemas.model import ResolutionInput
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_agent_llm(data: ResolutionInput) -> dict:
    """
    Resolution Agent using deterministic business logic.
    Handles exchange, cancel, refund, order tracking,
    complaints, and technical issues.
    """
    logger.info(f"🤖 RESOLUTION LLM: Processing resolution for order_id={data.order_id}, intent={data.intent}")

    intent = (data.intent or "").lower()

    # ✅ SAFE FALLBACKS (VERY IMPORTANT)
    product_name = data.product or "the product"
    description_value = data.description or ""
    quantity_value = data.quantity if data.quantity not in [None, 0, "0"] else "N/A"
    order_status = getattr(data, "status", None) or "processing"
    
    logger.debug(f"Product: {product_name}, Quantity: {quantity_value}, Status: {order_status}")

    # ----------------- DIRECT INTENTS -----------------

    # 1️⃣ Order Tracking
    if intent == "order_tracking":
        logger.info("Processing order tracking request")
        return {
            "action": "order_tracking",
            "message": (
                f"📦 Order Update\n\n"
                f"Your order {data.order_id} is currently {order_status}.\n"
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
        logger.info("Processing complaint")
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
        logger.info("Processing technical issue")
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
        logger.warning(f"Refund/Cancel denied for order {data.order_id}: {data.reason}")
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
# ----------------- RETURN CHECK -----------------

    if intent == "return" and not data.exchange_allowed:
        return {
            "action": "return_deny",
            "message": (
                f"❌ Return Not Allowed\n\n"
                f"Order **#{data.order_id}** is not eligible for return.\n"
                f"Reason: {data.reason}"
            ),
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    if intent == "return" and data.exchange_allowed:
        file_name = generate_return_label(
            data.order_id,
            product=product_name,
            description=description_value,
            quantity=data.quantity
        )
        return_label_url = f"http://localhost:8000/labels/{file_name}"

        return {
            "action": "return",
            "message": (
                f"✅ Your return request has been approved!\n\n"
                f"📦 Product: {product_name}\n"
                f"📝 Description: {description_value}\n" if description_value else ""
                f"🔢 Order ID: {data.order_id}\n"
                f"🔢 Quantity: {quantity_value}\n\n"
                f"📄 A prepaid return label has been generated.\n\n"
                f"Please print the label and ship the item back.\n"
                f"💰 Refund will be processed after inspection."
            ),
            "return_label_url": return_label_url,
            "refund_amount": None,
            "reason": None
        }

    # ----------------- EXCHANGE CHECK -----------------

    if intent == "exchange" and not data.exchange_allowed:
        return {
            "action": "exchange_deny",
            "message": (
                f"❌ Exchange Not Allowed\n\n"
                f"Order **#{data.order_id}** is not eligible for exchange.\n"
                f"Reason: {data.reason}"
            ),
            "return_label_url": None,
            "refund_amount": None,
            "reason": data.reason
        }

    if intent == "exchange" and data.exchange_allowed:
        file_name = generate_return_label(
            data.order_id,
            product=product_name,
            description=description_value,
            quantity=data.quantity
        )
        return_label_url = f"http://localhost:8000/labels/{file_name}"
        return {
            "action": "exchange",
            "message": (
                f"✅ Your exchange request has been approved!\n\n"
                f"📦 Product: {product_name}\n"
                f"📝 Description: {description_value}\n" if description_value else ""
                f"🔢 Order ID: {data.order_id}\n"
                f"🔢 Quantity: {quantity_value}\n\n"
                f"📄 A prepaid return label has been generated.\n\n"
                f"Please send the original item back.\n\n"
                f"🔁 Once received, we will ship your replacement item.\n\n"
               
            ),
            "return_label_url": return_label_url,
            "refund_amount": None,
            "reason": None
        }


    # Cancel / Refund
    if intent in ["cancel", "refund"] and data.cancel_allowed:
        logger.info(f"Processing refund/cancellation for order {data.order_id}, amount: {data.amount}")
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
    logger.warning(f"Unable to process intent '{intent}' for order {data.order_id}")
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
