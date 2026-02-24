"""
LLM-based policy evaluation functions for the policy agent.
Uses large language model to evaluate customer requests against policies.
"""
import json
from datetime import datetime
from app.utils.logger import get_logger
from app.agents.policy.app.rag.policy_llm import PolicyLLMClient
from app.agents.policy.app.prompts.policy_evaluation import (
    POLICY_CONTEXT,
    POLICY_EVALUATION_PROMPT,
    POLICY_INFO_PROMPT
)

try:
    import ollama
except ImportError:
    ollama = None

logger = get_logger(__name__)

# Initialize LLM client
_llm_client = None


def get_llm_client():
    """Get or create the LLM client."""
    global _llm_client
    if _llm_client is None:
        _llm_client = PolicyLLMClient(
            model="qwen2.5:0.5b",
            temperature=0.1
        )
    return _llm_client


def evaluate_policy_request(
    intent: str,
    order_details: dict = None
) -> dict:
    """
    Evaluate a customer request against company policies using LLM.
    
    Args:
        intent: Type of request (refund, return, exchange, cancel)
        order_details: Order information including status, delivered_date, etc.
        
    Returns:
        dict with keys: allowed (bool), reason (str), policy_type (str), policy_checked (bool)
    """
    if not order_details or order_details.get("status") == "Exchange Processed":
        logger.warning("No order details provided for policy evaluation")
        return {
            "allowed": False,
            "reason": "No order details available for evaluation",
            "policy_checked": True,
            "policy_type": intent
        }
    
    # Calculate days since delivery if available
    delivered_date = order_details.get("delivered_date")
    days_since_delivery = None
    
    if delivered_date:
        try:
            delivery_date = datetime.strptime(delivered_date, "%Y-%m-%d")
            days_since_delivery = (datetime.now() - delivery_date).days
            logger.debug(f"Days since delivery: {days_since_delivery}")
        except Exception as e:
            logger.warning(f"Could not calculate days since delivery: {e}")
    
    order_status = order_details.get("status", "Unknown")
    order_id = order_details.get("order_id")
    
    # Build the evaluation prompt
    prompt = POLICY_EVALUATION_PROMPT.format(
        policy_context=POLICY_CONTEXT,
        intent=intent,
        order_status=order_status,
        days_since_delivery=days_since_delivery if days_since_delivery is not None else "Unknown",
        delivered_date=delivered_date or "Not available",
        order_id=order_id or "Not provided",
        order_details=str(order_details)
    )
    
    logger.info(f"🤖 POLICY AGENT (LLM): Evaluating {intent} request for order {order_id}")
    logger.debug(f"Evaluation prompt:\n{prompt[:300]}...")
    
    # Call LLM client
    llm_client = get_llm_client()
    evaluation = llm_client.evaluate(prompt)
    
    # Add metadata
    evaluation["policy_checked"] = True
    evaluation["policy_type"] = intent
    
    if "error" in evaluation:
        logger.error(f"LLM evaluation error: {evaluation['error']}")
    else:
        logger.info(
            f"✅ POLICY (LLM): {intent.upper()} {'ALLOWED' if evaluation.get('allowed') else 'DENIED'} - "
            f"{evaluation.get('reason', 'No reason provided')}"
        )
    
    return evaluation


def get_policy_information(policy_type: str = None) -> dict:
    """
    Return policy information for informational queries using LLM.
    Does not require order details - just returns policy rules.
    
    Args:
        policy_type: Type of policy (refund, return, exchange, cancel) or None for general info
        
    Returns:
        dict with structured policy information including title, eligibility, details, processing_time, and message
    """
    logger.info(f"📚 POLICY AGENT (LLM): Fetching policy information for {policy_type or 'general'}")
    
    if policy_type:
        query = f"Tell me about the {policy_type} policy"
    else:
        query = "What are all your customer service policies?"
    
    prompt = POLICY_INFO_PROMPT.format(query=query)
    
    llm_client = get_llm_client()
    
    try:
        if ollama is None:
            logger.warning("Ollama not available, using fallback policy information")
            return _fallback_policy_info(policy_type)
            
        response = ollama.chat(
            model="qwen2.5:0.5b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )
        
        message = response.get("message", {}).get("content", "")
        
        # Try to parse JSON response
        try:
            # Clean up potential markdown formatting
            if "```json" in message:
                message = message.split("```json")[1].split("```")[0].strip()
            elif "```" in message:
                message = message.split("```")[1].split("```")[0].strip()
            
            policy_data = json.loads(message)
            policy_data["policy_type"] = policy_type or "all"
            return policy_data
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse policy response as JSON: {e}")
            # Fallback to rule-based approach
            return _fallback_policy_info(policy_type)
    except Exception as e:
        logger.error(f"Failed to fetch policy information: {e}")
        # Fallback to rule-based approach
        return _fallback_policy_info(policy_type)


def _fallback_policy_info(policy_type: str = None) -> dict:
    """
    Fallback policy information if LLM is unavailable.
    Returns structured policy data.
    """
    policies = {
        "refund": {
            "title": "Refund Policy",
            "eligibility": "Within 30 days of delivery",
            "details": [
                "Orders must be in 'Delivered' status",
                "Refunds are processed within 5-7 business days",
                "Refunds go to original payment method"
            ],
            "processing_time": "5-7 business days",
            "message": "We offer refunds within 30 days of delivery for delivered orders. Once approved, refunds are processed within 5-7 business days to your original payment method."
        },
        "return": {
            "title": "Return Policy",
            "eligibility": "Within 45 days of delivery",
            "details": [
                "Order must be in 'Delivered' status",
                "We provide a prepaid return label via email",
                "Items are inspected before refund is processed",
                "We accept returns for most items in original condition"
            ],
            "processing_time": "3-5 business days after receiving item",
            "message": "Returns are accepted within 45 days of delivery. The order must be in 'Delivered' status. We provide a prepaid return label via email. Once we receive and inspect the item, we'll process your refund."
        },
        "exchange": {
            "title": "Exchange Policy",
            "eligibility": "Within 45 days of delivery",
            "details": [
                "Same rules as returns - available within 45 days of delivery",
                "You can exchange for a different size or color",
                "We'll send you a prepaid return label for the original item",
                "New item shipped after we receive the original"
            ],
            "processing_time": "3-5 business days after receiving original item",
            "message": "Exchanges follow the same rules as returns - available within 45 days of delivery. You can exchange for a different size or color. We'll send you a prepaid return label for the original item."
        },
        "cancel": {
            "title": "Cancellation Policy",
            "eligibility": "Before the order ships",
            "details": [
                "Orders can be cancelled before they ship",
                "Cannot cancel delivered orders (request return or refund instead)",
                "Cancellations process immediately",
                "No charge for cancelled orders"
            ],
            "processing_time": "Immediate",
            "message": "Orders can be cancelled before they ship. Once an order is delivered, you'll need to request a return or refund instead. Cancellations are processed immediately."
        }
    }
    
    if policy_type and policy_type in policies:
        policy_data = policies[policy_type].copy()
        policy_data["policy_type"] = policy_type
        return policy_data
    
    # Return all policies if no specific type requested
    if policy_type == "all" or policy_type is None:
        return {
            "policy_type": "all",
            "title": "All Customer Service Policies",
            "policies": [
                {
                    "policy_type": ptype,
                    **policies[ptype]
                }
                for ptype in ["refund", "return", "exchange", "cancel"]
            ],
            "message": "Here are our customer service policies. If you need help with a specific order, please provide your order ID and I'll be happy to assist!"
        }
    
    # Default fallback
    return {
        "policy_type": "all",
        "title": "Customer Service Policies",
        "message": "Here are our customer service policies. If you need help with a specific order, please provide your order ID and I'll be happy to assist!"
    }
