from datetime import datetime, timedelta
from app.orchestrator.guard import agent_guard
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_policy_information(policy_type: str = None) -> dict:
    """
    Return policy information for informational queries.
    Does not require order details - just returns policy rules.
    
    Args:
        policy_type: Type of policy (refund, return, exchange, cancel) or None for general info
        
    Returns:
        dict with policy information
    """
    policies = {
        "refund": {
            "title": "Refund Policy",
            "details": "We offer refunds within 30 days of delivery for delivered orders. The order must be in 'Delivered' status. Once approved, refunds are processed within 5-7 business days to your original payment method."
        },
        "return": {
            "title": "Return Policy", 
            "details": "Returns are accepted within 45 days of delivery. The order must be in 'Delivered' status. We provide a prepaid return label via email. Once we receive and inspect the item, we'll process your refund."
        },
        "exchange": {
            "title": "Exchange Policy",
            "details": "Exchanges follow the same rules as returns - available within 45 days of delivery. You can exchange for a different size or color. We'll send you a prepaid return label for the original item."
        },
        "cancel": {
            "title": "Cancellation Policy",
            "details": "Orders can be cancelled before they ship. Once an order is shipped or delivered, you'll need to request a return or refund instead. Cancellations are processed immediately."
        }
    }
    
    if policy_type and policy_type in policies:
        return {
            "policy_type": policy_type,
            "message": f"**{policies[policy_type]['title']}**\n\n{policies[policy_type]['details']}"
        }
    
    # Return all policies if no specific type requested
    all_policies = "\n\n".join([
        f"**{p['title']}**\n{p['details']}" 
        for p in policies.values()
    ])
    
    return {
        "policy_type": "all",
        "message": f"Here are our customer service policies:\n\n{all_policies}\n\nIf you need help with a specific order, please provide your order ID and I'll be happy to assist!"
    }


def check_refund_policy(order_details: dict) -> dict:
    """
    Check if order is eligible for refund based on policy rules.
    
    Policy Rules:
    1. Order must be delivered
    2. Refund window is 30 days from delivery
    3. Status must not be "Cancelled" or "Refunded"
    """
    if not order_details:
        return {
            "allowed": False,
            "reason": "No order details available"
        }
    
    status = order_details.get("status")
    delivered_date = order_details.get("delivered_date")
    
    # Check if order is delivered
    if status != "Delivered":
        return {
            "allowed": False,
            "reason": f"Order status is '{status}'. Refunds only available for delivered orders."
        }
    
    # Check if delivered_date is available
    if not delivered_date:
        return {
            "allowed": False,
            "reason": "Delivery date not found"
        }
    
    # Check if within 30-day window
    try:
        delivery_date = datetime.strptime(delivered_date, "%Y-%m-%d")
        days_since_delivery = (datetime.now() - delivery_date).days
        
        if days_since_delivery > 30:
            return {
                "allowed": False,
                "reason": f"Refund window expired ({days_since_delivery} days since delivery, limit is 30 days)"
            }
        
        return {
            "allowed": True,
            "reason": f"Order eligible for refund ({days_since_delivery} days since delivery)"
        }
        
    except Exception as e:
        return {
            "allowed": False,
            "reason": f"Error checking refund eligibility: {str(e)}"
        }


def check_return_policy(order_details: dict) -> dict:
    """
    Check if order is eligible for return.
    
    Policy Rules:
    1. Return window is 45 days from delivery
    2. Order must be delivered
    """
    if not order_details:
        return {
            "allowed": False,
            "reason": "No order details available"
        }
    
    status = order_details.get("status")
    delivered_date = order_details.get("delivered_date")
    
    if status != "Delivered":
        return {
            "allowed": False,
            "reason": f"Order status is '{status}'. Returns only available for delivered orders."
        }
    
    if not delivered_date:
        return {
            "allowed": False,
            "reason": "Delivery date not found"
        }
    
    try:
        delivery_date = datetime.strptime(delivered_date, "%Y-%m-%d")
        days_since_delivery = (datetime.now() - delivery_date).days
        
        if days_since_delivery > 45:
            return {
                "allowed": False,
                "reason": f"Return window expired ({days_since_delivery} days since delivery, limit is 45 days)"
            }
        
        return {
            "allowed": True,
            "reason": f"Order eligible for return ({days_since_delivery} days since delivery)"
        }
        
    except Exception as e:
        return {
            "allowed": False,
            "reason": f"Error checking return eligibility: {str(e)}"
        }


def check_exchange_policy(order_details: dict) -> dict:
    """
    Check if order is eligible for exchange.
    Same rules as return policy.
    """
    return check_return_policy(order_details)


@agent_guard("policy")
async def policy_agent(state):
    """
    Policy Agent: Checks if the requested action is allowed based on company policies.
    
    Expects:
        - state["intent"] (from triage)
        - state["entities"]["order_details"] (from database)
        
    Sets:
        - state["entities"]["policy_result"] with policy check result
        - state["current_state"] to "RESOLUTION" on success
    """
    logger.info("🔒 POLICY AGENT: Starting policy validation")
    
    intent = state.get("intent")
    order_details = state.get("entities", {}).get("order_details") or state.get("order_details")
    
    logger.debug(f"Intent: {intent}, Order details present: {order_details is not None}")
    
    # Initialize policy result
    policy_result = {
        "allowed": False,
        "reason": "Unknown intent",
        "policy_checked": False
    }
    
    # Check policy based on intent
    if intent == "refund":
        logger.info("Checking refund policy")
        policy_result = check_refund_policy(order_details)
        policy_result["policy_checked"] = True
        policy_result["policy_type"] = "refund"
        logger.info(f"✅ POLICY: Refund {'ALLOWED' if policy_result['allowed'] else 'DENIED'} - {policy_result['reason']}")
        
    elif intent == "return":
        logger.info("Checking return policy")
        policy_result = check_return_policy(order_details)
        policy_result["policy_checked"] = True
        policy_result["policy_type"] = "return"
        logger.info(f"✅ POLICY: Return {'ALLOWED' if policy_result['allowed'] else 'DENIED'} - {policy_result['reason']}")
        
    elif intent == "exchange":
        logger.info("Checking exchange policy")
        policy_result = check_exchange_policy(order_details)
        policy_result["policy_checked"] = True
        policy_result["policy_type"] = "exchange"
        logger.info(f"✅ POLICY: Exchange {'ALLOWED' if policy_result['allowed'] else 'DENIED'} - {policy_result['reason']}")
        
    elif intent == "cancel":
        logger.info("Checking cancellation policy")
        # Cancellation policy check - can only cancel if not shipped/delivered
        status = order_details.get("status") if order_details else None
        logger.debug(f"Order status: {status}")
        
        if status in ["Delivered", "Shipped"]:
            policy_result = {
                "allowed": False,
                "reason": f"Order has already been {status.lower()}. Cancellations are only available before shipping.",
                "policy_checked": True,
                "policy_type": "cancel"
            }
            logger.info(f"❌ POLICY: Cancellation DENIED - Order already {status}")
        elif status == "Cancelled":
            policy_result = {
                "allowed": False,
                "reason": "Order has already been cancelled.",
                "policy_checked": True,
                "policy_type": "cancel"
            }
            logger.info("❌ POLICY: Cancellation DENIED - Already cancelled")
        else:
            policy_result = {
                "allowed": True,
                "reason": "Order is eligible for cancellation.",
                "policy_checked": True,
                "policy_type": "cancel"
            }
            logger.info("✅ POLICY: Cancellation ALLOWED")
        
    elif intent == "order_tracking":
        logger.info("Order tracking - no policy check required")
        # Tracking doesn't need policy check
        policy_result = {
            "allowed": True,
            "reason": "Order tracking information available",
            "policy_checked": False
        }
        
    elif intent in ["complaint", "technical_issue", "general_question"]:
        logger.info(f"Intent '{intent}' - no policy check required")
        # These intents don't require policy checks
        policy_result = {
            "allowed": True,
            "reason": "No policy check required for this intent",
            "policy_checked": False
        }
    else:
        logger.warning(f"Unknown intent: {intent}")
    
    # Store policy result in state
    state["entities"]["policy_result"] = policy_result
    
    # Move to resolution regardless of policy result
    # Resolution agent will handle the response based on policy
    state["current_state"] = "RESOLUTION"
    logger.info("🔄 POLICY: Moving to RESOLUTION state")
    
    return state