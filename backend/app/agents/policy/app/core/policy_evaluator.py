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
    if not order_details:
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


def _fetch_policy_from_rag(policy_type: str) -> dict:
    """
    Fetch detailed policy information from RAG system.
    
    Args:
        policy_type: Type of policy (refund, return, exchange, cancel)
        
    Returns:
        dict with RAG-fetched policy details or None if RAG is unavailable
    """
    try:
        from app.agents.policy.app.rag.service import RAGService
        from app.agents.policy.app.core.models import QueryRequest
        
        logger.info(f"🔍 Attempting to fetch {policy_type} policy from RAG system...")
        
        rag_service = RAGService.get_instance()
        
        # Initialize RAG if not already done
        if not rag_service._initialized:
            logger.info("Initializing RAG service...")
            rag_service.initialize()
        
        # Build meaningful queries for each policy type
        query_map = {
            "refund": f"How can I get a refund? What is the refund policy and process?",
            "return": f"How do I return an item? What is the return policy?",
            "exchange": f"Can I exchange an item? What is the exchange policy?",
            "cancel": f"How do I cancel my order? What is the cancellation policy?"
        }
        
        query = query_map.get(policy_type, f"Tell me about the {policy_type} policy")
        
        request = QueryRequest(
            query=query,
            conversation_history=[],
            filter_domain=policy_type
        )
        
        response = rag_service.query(request)
        
        if response and response.answer:
            logger.info(f"✅ Successfully fetched {policy_type} details from RAG")
            return {
                "policy_type": policy_type,
                "rag_content": response.answer,
                "source": "rag"
            }
        else:
            logger.warning(f"RAG returned empty response for {policy_type}")
            return None
            
    except Exception as e:
        logger.warning(f"Failed to fetch from RAG: {str(e)}. Will fall back to other methods.")
        return None


def _format_policy_response(
    policy_type: str,
    rag_data: dict = None,
    fallback_data: dict = None
) -> dict:
    """
    Format policy information into a detailed, structured response.
    
    Args:
        policy_type: Type of policy
        rag_data: Data fetched from RAG system
        fallback_data: Fallback static data
        
    Returns:
        Formatted policy response dict
    """
    # Use RAG data if available, otherwise fallback
    source_data = rag_data if rag_data else fallback_data
    
    if not source_data:
        logger.warning("No policy data available")
        return _fallback_policy_info(policy_type)
    
    # If RAG provided content, use it to enhance the response
    if rag_data and rag_data.get("source") == "rag":
        rag_content = rag_data.get("rag_content", "")
        
        # Structure the response with RAG content
        policy_info = fallback_data.copy() if fallback_data else {}
        policy_info["policy_type"] = policy_type
        policy_info["detailed_content"] = rag_content
        policy_info["source"] = "rag"
        
        # Enhance the message with RAG-derived information
        policy_info["message"] = _build_enhanced_message(
            policy_type,
            policy_info.get("title", ""),
            rag_content,
            policy_info.get("eligibility", "")
        )
        
        return policy_info
    
    # Return formatted fallback data
    return source_data


def _build_enhanced_message(
    policy_type: str,
    title: str,
    rag_content: str,
    eligibility: str
) -> str:
    """
    Build an enhanced, user-friendly policy message from available data.
    
    Args:
        policy_type: Type of policy
        title: Policy title
        rag_content: Content from RAG system
        eligibility: Eligibility information
        
    Returns:
        Formatted message string
    """
    lines = [f"📋 **{title}**"]
    
    if eligibility:
        lines.append(f"\n⏰ **Eligibility Window:** {eligibility}")
    
    # Add RAG content (extract key sentences)
    if rag_content:
        lines.append("\n**Key Details:**")
        # Extract first few sentences from RAG content
        sentences = rag_content.split(". ")[:3]
        for sentence in sentences:
            if sentence.strip():
                lines.append(f"• {sentence.strip()}.")
    
    lines.append("\n\nWould you like more specific details about this policy, or do you have questions about a specific order?")
    
    return "\n".join(lines)


def get_policy_information(policy_type: str = None) -> dict:
    """
    Return detailed, structured policy information for informational queries.
    Uses RAG system to fetch real company policy data, with intelligent fallbacks.
    
    Does not require order details - just returns policy rules and processes.
    
    Args:
        policy_type: Type of policy (refund, return, exchange, cancel) or None for general info
        
    Returns:
        dict with structured policy information including:
        - policy_type: Type of policy
        - title: Policy title
        - eligibility: Eligibility window
        - details: List of key details
        - processing_time: Expected processing time
        - message: Human-readable formatted message
        - detailed_content: (Optional) Detailed info from RAG system
        - source: Source of information (rag/fallback)
    """
    logger.info(f"📚 POLICY AGENT: Fetching detailed policy information for {policy_type or 'general'}")
    
    # Get fallback static data for structure
    fallback_data = _fallback_policy_info(policy_type)
    
    # If no specific policy type, return all policies with basic info
    if not policy_type or policy_type == "all":
        logger.info("Returning all policies information")
        all_policies = fallback_data
        all_policies["source"] = "static"
        return all_policies
    
    # Try to fetch from RAG system for detailed information
    rag_data = _fetch_policy_from_rag(policy_type)
    
    # Format and return the response (with RAG data if available)
    response = _format_policy_response(policy_type, rag_data, fallback_data)
    
    logger.info(f"✅ Policy information prepared for {policy_type}")
    return response


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
