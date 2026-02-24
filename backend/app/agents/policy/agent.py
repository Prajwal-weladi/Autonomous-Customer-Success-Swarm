from app.orchestrator.guard import agent_guard
from app.utils.logger import get_logger
from app.agents.database.db_service import check_existing_request
from app.agents.policy.app.core.policy_evaluator import (
    evaluate_policy_request,
    get_policy_information,
    _fallback_policy_info,
    _fetch_policy_from_rag,
    _format_policy_response
)

logger = get_logger(__name__)


def get_detailed_policy_info(
    policy_type: str = None,
    conversation_history: list = None
) -> dict:
    """
    Fetch detailed policy information using advanced RAG pipeline.
    
    Single unified function for fetching policy info - used by both API and pipeline handlers.
    Combines RAG retrieval with structured formatting.
    
    Args:
        policy_type: Type of policy (refund, return, exchange, cancel) or None for general
        conversation_history: Previous conversation context
        
    Returns:
        Structured dict with policy information including:
        - policy_type: Policy type
        - title: Policy title
        - eligibility: Eligibility window
        - details: List of key details
        - processing_time: Processing timeline
        - message: Formatted user-friendly message
        - detailed_content: RAG-fetched detailed info (if available)
        - source: Source of information (rag/static)
    """
    logger.debug(f"[POLICY] Fetching info: {policy_type or 'general'}")
    
    # Get fallback/base data
    fallback_data = _fallback_policy_info(policy_type)
    
    # If no specific type, return all policies
    if not policy_type or policy_type == "all":
        logger.debug(f"[POLICY] Returning all policies (static data)")
        fallback_data["source"] = "static"
        return fallback_data
    
    # Try to fetch from RAG for detailed information
    rag_data = _fetch_policy_from_rag(policy_type)
    
    # Format response with RAG data if available
    response = _format_policy_response(policy_type, rag_data, fallback_data)
    
    logger.debug(f"[POLICY] Info retrieved")
    return response


def check_refund_policy(order_details: dict) -> dict:
    """
    Check if order is eligible for refund (LLM-based evaluation).
    
    This function has been migrated to use LLM-based evaluation
    instead of hard-coded rule-based logic.
    
    Args:
        order_details: Order information
        
    Returns:
        dict with allowed (bool) and reason (str)
    """
    return evaluate_policy_request("refund", order_details)


def check_return_policy(order_details: dict) -> dict:
    """
    Check if order is eligible for return (LLM-based evaluation).
    
    This function has been migrated to use LLM-based evaluation
    instead of hard-coded rule-based logic.
    
    Args:
        order_details: Order information
        
    Returns:
        dict with allowed (bool) and reason (str)
    """
    return evaluate_policy_request("return", order_details)


def check_exchange_policy(order_details: dict) -> dict:
    """
    Check if order is eligible for exchange (LLM-based evaluation).
    
    This function has been migrated to use LLM-based evaluation
    instead of hard-coded rule-based logic.
    
    Args:
        order_details: Order information
        
    Returns:
        dict with allowed (bool) and reason (str)
    """
    return evaluate_policy_request("exchange", order_details)


@agent_guard("policy")
async def policy_agent(state):
    """
    Policy Agent (LLM-Based): Evaluates customer requests against company policies using an LLM.
    
    Expects:
        - state["intent"] (from triage)
        - state["entities"]["order_details"] (from database)
        
    Sets:
        - state["entities"]["policy_result"] with policy evaluation result
        - state["current_state"] to "RESOLUTION" on success
        
    The agent uses LLM-based evaluation for policy decisions instead of hard-coded rules.
    This allows for more nuanced policy interpretation and better explanation of decisions.
    """
    logger.info("🔒 POLICY AGENT (LLM-BASED): Starting policy evaluation")
    
    intent = state.get("intent")
    order_details = state.get("entities", {}).get("order_details") or state.get("order_details")
    
    # 1. Check if an approved request already exists for this order
    if intent in ["refund", "return", "exchange"]:
        order_id = order_details.get("order_id") if order_details else None
        if order_id:
            existing_request = check_existing_request(order_id)
            if existing_request:
                logger.warning(f"Blocking request: order {order_id} already has an approved {existing_request.request_type}")
                state["entities"]["policy_result"] = {
                    "allowed": False,
                    "reason": f"An approved {existing_request.request_type} request already exists for order #{order_id}. Please cancel the previous request before submitting a new one.",
                    "policy_checked": True,
                    "policy_type": intent
                }
                state["current_state"] = "RESOLUTION"
                return state

    # 2. Evaluate policy based on intent (now using LLM)
    if intent == "refund":
        logger.info("Evaluating refund policy using LLM")
        policy_result = evaluate_policy_request("refund", order_details)
        logger.info(f"✅ POLICY (LLM): Refund {'ALLOWED' if policy_result.get('allowed') else 'DENIED'} - {policy_result.get('reason')}")
        
    elif intent == "return":
        logger.info("Evaluating return policy using LLM")
        policy_result = evaluate_policy_request("return", order_details)
        logger.info(f"✅ POLICY (LLM): Return {'ALLOWED' if policy_result.get('allowed') else 'DENIED'} - {policy_result.get('reason')}")
        
    elif intent == "exchange":
        logger.info("Evaluating exchange policy using LLM")
        policy_result = evaluate_policy_request("exchange", order_details)
        logger.info(f"✅ POLICY (LLM): Exchange {'ALLOWED' if policy_result.get('allowed') else 'DENIED'} - {policy_result.get('reason')}")
        
    elif intent == "cancel":
        logger.info("Evaluating cancellation policy using LLM")
        policy_result = evaluate_policy_request("cancel", order_details)
        logger.info(f"✅ POLICY (LLM): Cancellation {'ALLOWED' if policy_result.get('allowed') else 'DENIED'} - {policy_result.get('reason')}")

    elif intent == "order_tracking":
        logger.info("Order tracking - no policy evaluation required")
        policy_result = {
            "allowed": True,
            "reason": "No policy validation required for order tracking",
            "policy_checked": False,
            "policy_type": None
        }
        
    elif intent in ["complaint", "technical_issue", "general_question"]:
        logger.info(f"No policy evaluation required for intent '{intent}'")
        policy_result = {
            "allowed": True,
            "reason": f"No policy validation required for '{intent}'",
            "policy_checked": False,
            "policy_type": None
        }
        
    else:
        # Default: allow resolution to handle any remaining intents safely
        logger.debug(f"Unrecognized intent '{intent}', allowing resolution to handle")
        policy_result = {
            "allowed": True,
            "reason": f"No policy validation required for '{intent}'",
            "policy_checked": False,
            "policy_type": None
        }
    
    # Set the policy result in state
    state["entities"]["policy_result"] = policy_result
    state["current_state"] = "RESOLUTION"
    
    logger.info("🔄 POLICY: Moving to RESOLUTION state")
    return state
