from app.orchestrator.guard import agent_guard


def generate_refund_response(state) -> str:
    """Generate response for refund requests"""
    policy_result = state["entities"].get("policy_result", {})
    order_details = state["entities"].get("order_details", {})
    
    if policy_result.get("allowed"):
        order_id = order_details.get("order_id")
        product = order_details.get("product")
        return f"Good news! Your refund request for order #{order_id} ({product}) has been approved. The refund will be processed within 5-7 business days to your original payment method. You'll receive a confirmation email shortly."
    else:
        reason = policy_result.get("reason", "Policy requirements not met")
        return f"I'm sorry, but we cannot process a refund for this order. Reason: {reason}. If you believe this is an error, I can connect you with a specialist who can review your case."


def generate_return_response(state) -> str:
    """Generate response for return requests"""
    policy_result = state["entities"].get("policy_result", {})
    order_details = state["entities"].get("order_details", {})
    
    if policy_result.get("allowed"):
        order_id = order_details.get("order_id")
        product = order_details.get("product")
        return f"Your return request for order #{order_id} ({product}) has been approved! I'll generate a prepaid return label and email it to you within the next 30 minutes. Please pack the item securely and drop it off at any shipping location. Once we receive and inspect the item, we'll process your refund."
    else:
        reason = policy_result.get("reason", "Policy requirements not met")
        return f"I'm sorry, but we cannot process a return for this order. Reason: {reason}. Would you like me to connect you with a specialist?"


def generate_exchange_response(state) -> str:
    """Generate response for exchange requests"""
    policy_result = state["entities"].get("policy_result", {})
    order_details = state["entities"].get("order_details", {})
    
    if policy_result.get("allowed"):
        order_id = order_details.get("order_id")
        product = order_details.get("product")
        return f"Your exchange request for order #{order_id} ({product}) has been approved! Please let me know what size/color you'd like to exchange it for, and I'll process the exchange. We'll send you a prepaid return label via email for the original item."
    else:
        reason = policy_result.get("reason", "Policy requirements not met")
        return f"I'm sorry, but we cannot process an exchange for this order. Reason: {reason}. Can I help you with anything else?"


def generate_tracking_response(state) -> str:
    """Generate response for order tracking requests"""
    order_details = state["entities"].get("order_details", {})
    
    if not order_details:
        return "I couldn't find tracking information for this order. Please verify your order number and try again, or I can connect you with a specialist."
    
    order_id = order_details.get("order_id")
    product = order_details.get("product")
    status = order_details.get("status")
    order_date = order_details.get("order_date")
    delivered_date = order_details.get("delivered_date")
    
    if status == "Delivered":
        return f"Order #{order_id} ({product}) was delivered on {delivered_date}. If you haven't received it, please check with neighbors or building management. Need further assistance?"
    elif status == "Shipped":
        return f"Order #{order_id} ({product}) is currently in transit. It was shipped on {order_date} and should arrive soon. You'll receive a notification once it's delivered."
    else:
        return f"Order #{order_id} ({product}) is currently {status}. Order placed on {order_date}. If you need more details, I can connect you with our shipping team."


def generate_complaint_response(state) -> str:
    """Generate response for complaints"""
    user_issue = state["entities"].get("user_issue", "")
    order_details = state["entities"].get("order_details", {})
    
    if order_details:
        order_id = order_details.get("order_id")
        return f"I'm truly sorry to hear about your experience with order #{order_id}. Your feedback is important to us. I've documented your complaint and escalated it to our quality team. A specialist will contact you within 24 hours to address your concerns. In the meantime, is there anything I can help resolve right now?"
    else:
        return f"I'm truly sorry to hear about your experience. Your feedback is important to us. I've documented your complaint and a specialist will contact you within 24 hours. Can you provide more details so we can better assist you?"


def generate_general_response(state) -> str:
    """Generate response for general questions"""
    user_issue = state["entities"].get("user_issue", "")
    return f"Thank you for reaching out! I'd be happy to help with your question. However, for the most accurate information, I recommend connecting you with a specialist who can provide detailed assistance. Would you like me to arrange that?"


def generate_technical_issue_response(state) -> str:
    """Generate response for technical issues"""
    return "I understand you're experiencing a technical issue. I've logged this problem with our technical support team. They'll investigate and reach out to you within 4 hours. In the meantime, have you tried restarting your device or clearing your browser cache?"


@agent_guard("resolution")
async def resolution_agent(state):
    """
    Resolution Agent: Generates the final response based on intent and policy check results.
    
    Expects:
        - state["intent"] (from triage)
        - state["entities"]["policy_result"] (from policy)
        - state["entities"]["order_details"] (from database)
        
    Sets:
        - state["reply"] with the final customer response
        - state["status"] to "completed"
        - state["current_state"] to "COMPLETED"
    """
    intent = state.get("intent", "unknown")
    
    # Generate response based on intent
    if intent == "refund":
        reply = generate_refund_response(state)
    elif intent == "return":
        reply = generate_return_response(state)
    elif intent == "exchange":
        reply = generate_exchange_response(state)
    elif intent == "order_tracking":
        reply = generate_tracking_response(state)
    elif intent == "complaint":
        reply = generate_complaint_response(state)
    elif intent == "technical_issue":
        reply = generate_technical_issue_response(state)
    elif intent == "general_question":
        reply = generate_general_response(state)
    else:
        # Unknown intent
        reply = "I'm not quite sure how to help with that. Let me connect you with a human agent who can better assist you."
        state["current_state"] = "HUMAN_HANDOFF"
        state["status"] = "handoff"
        state["reply"] = reply
        return state
    
    # Set final response
    state["reply"] = reply
    state["status"] = "completed"
    state["current_state"] = "COMPLETED"
    
    return state