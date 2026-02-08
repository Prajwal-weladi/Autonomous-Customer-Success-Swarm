from datetime import datetime, timedelta
from app.orchestrator.guard import agent_guard


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
    intent = state.get("intent")
    order_details = state["entities"].get("order_details")
    
    # Initialize policy result
    policy_result = {
        "allowed": False,
        "reason": "Unknown intent",
        "policy_checked": False
    }
    
    # Check policy based on intent
    if intent == "refund":
        policy_result = check_refund_policy(order_details)
        policy_result["policy_checked"] = True
        policy_result["policy_type"] = "refund"
        
    elif intent == "return":
        policy_result = check_return_policy(order_details)
        policy_result["policy_checked"] = True
        policy_result["policy_type"] = "return"
        
    elif intent == "exchange":
        policy_result = check_exchange_policy(order_details)
        policy_result["policy_checked"] = True
        policy_result["policy_type"] = "exchange"
        
    elif intent == "order_tracking":
        # Tracking doesn't need policy check
        policy_result = {
            "allowed": True,
            "reason": "Order tracking information available",
            "policy_checked": False
        }
        
    elif intent in ["complaint", "technical_issue", "general_question"]:
        # These intents don't require policy checks
        policy_result = {
            "allowed": True,
            "reason": "No policy check required for this intent",
            "policy_checked": False
        }
    
    # Store policy result in state
    state["entities"]["policy_result"] = policy_result
    
    # Move to resolution regardless of policy result
    # Resolution agent will handle the response based on policy
    state["current_state"] = "RESOLUTION"
    
    return state