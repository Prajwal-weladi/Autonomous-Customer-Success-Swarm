import json
import re

from app.orchestrator.guard import agent_guard
from app.agents.triage.prompts import TRIAGE_PROMPT

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: ollama not available, using rule-based triage only")

INTENT_RULES = {
    "policy_info": ["policy", "refund policy", "return policy", "exchange policy", "cancellation policy", "cancel policy", "how does", "what is your", "tell me about", "what are the", "explain"],
    "cancel": ["cancel order", "cancel my order", "cancel this order", "want to cancel"],
    "refund": ["refund", "money back", "get my money"],
    "return": ["return", "send back", "don't want"],
    "exchange": ["exchange", "replace", "swap", "different size", "different color"],
    "order_tracking": ["where is my order", "track", "order status", "hasn't arrived", "not received", "check status", "check my order", "status of order", "status for order"],
    "complaint": ["bad", "worst", "terrible", "not happy", "angry", "disappointed", "poor quality"],
    "technical_issue": ["not working", "error", "bug", "broken", "defective"],
}

URGENT_WORDS = ["urgent", "now", "immediately", "asap", "emergency", "right now"]


def extract_order_id(text: str) -> str | None:
    """Extract order ID after 'order' or 'id' keyword"""
    match = re.search(r'(?:order\s*)?id\s*(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # fallback: order 3456
    match = re.search(r'order\s*(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def rule_based_intent(text: str) -> str | None:
    """Determine intent using keyword matching"""
    text_lower = text.lower()
    for intent, keywords in INTENT_RULES.items():
        for keyword in keywords:
            if keyword in text_lower:
                return intent
    return None


def rule_based_urgency(text: str) -> str:
    """Determine urgency using keyword matching"""
    text_lower = text.lower()
    for word in URGENT_WORDS:
        if word in text_lower:
            return "high"
    
    # Check for complaint-related urgency
    if any(word in text_lower for word in ["angry", "terrible", "worst"]):
        return "high"
    
    return "normal"


def run_triage(message: str) -> dict:
    """
    Main triage function that analyzes user message.
    Uses LLM if available, falls back to rules.
    """
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    
    logger.info(f"🔍 TRIAGE: Analyzing message: '{message[:100]}...'")
    
    text = message.lower()
    order_id = extract_order_id(message)
    urgency = rule_based_urgency(text)
    fallback_intent = rule_based_intent(text) or "unknown"
    
    logger.debug(f"Rule-based extraction: intent={fallback_intent}, order_id={order_id}, urgency={urgency}")

    # If Ollama is not available, use rule-based only
    if not OLLAMA_AVAILABLE:
        logger.warning("⚠️ TRIAGE: Ollama not available, using rule-based analysis only")
        return {
            "intent": fallback_intent,
            "urgency": urgency,
            "order_id": order_id,
            "confidence": 0.60,
            "user_issue": message
        }

    # Try to use LLM for better analysis
    try:
        logger.debug("Attempting LLM-based triage analysis")
        prompt = TRIAGE_PROMPT.format(message=message)
        response = ollama.chat(
            model="qwen2.5:0.5b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}  # Lower temperature for more consistent output
        )

        output = response.get("message", {}).get("content", "")

        # Try to parse JSON response
        try:
            # Clean up potential markdown formatting
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()
            
            result = json.loads(output)
            
            # ✅ SANITIZE order_id - ensure it's either a valid number or None
            order_id_value = result.get("order_id")
            if order_id_value:
                # Check if it's a string with placeholder text
                if isinstance(order_id_value, str):
                    # List of invalid placeholder phrases
                    invalid_phrases = [
                        "present if available",
                        "not provided",
                        "none",
                        "null",
                        "n/a",
                        "not found",
                        "not mentioned",
                        "not specified",
                        "if available",
                        "in the message"
                    ]
                    
                    # Check if it contains any invalid phrases
                    order_id_lower = order_id_value.lower()
                    if any(phrase in order_id_lower for phrase in invalid_phrases):
                        logger.debug(f"Removing invalid placeholder order_id: '{order_id_value}'")
                        result["order_id"] = None
                    else:
                        # Try to extract just the number
                        import re
                        match = re.search(r'\d+', order_id_value)
                        if match:
                            result["order_id"] = match.group()
                            logger.debug(f"Extracted order_id number: {result['order_id']}")
                        else:
                            # No number found, set to None
                            logger.debug(f"No number found in order_id '{order_id_value}', setting to None")
                            result["order_id"] = None
            
            # Validate and fill in missing fields with fallbacks
            result["order_id"] = result.get("order_id") or order_id
            result["urgency"] = result.get("urgency") or urgency
            result["intent"] = result.get("intent") or fallback_intent
            result["confidence"] = result.get("confidence", 0.70)
            result["user_issue"] = result.get("user_issue") or message
            
            logger.info(f"✅ TRIAGE (LLM): intent={result['intent']}, order_id={result['order_id']}, confidence={result['confidence']}")
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM output as JSON: {e}")
            logger.debug(f"LLM output was: {output[:200]}")
            # Fall back to rule-based
            return {
                "intent": fallback_intent,
                "urgency": urgency,
                "order_id": order_id,
                "confidence": 0.50,
                "user_issue": message
            }
            
    except Exception as e:
        logger.error(f"LLM triage failed: {e}", exc_info=True)
        # Fall back to rule-based
        return {
            "intent": fallback_intent,
            "urgency": urgency,
            "order_id": order_id,
            "confidence": 0.50,
            "user_issue": message
        }


@agent_guard("triage")
async def triage_agent(state):
    """
    Triage Agent: Analyzes user message to determine intent, urgency, and extract entities.
    """
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    
    logger.info(f"🔍 TRIAGE AGENT: Processing message")
    message = state.get("user_message") or ""
    
    if not message:
        logger.error("❌ TRIAGE: Empty user message")
        state["last_error"] = "Empty user message"
        state["current_state"] = "HUMAN_HANDOFF"
        return state
    
    # Run triage analysis
    result = run_triage(message)
    logger.info(f"✅ TRIAGE: Detected intent={result.get('intent')}, order_id={result.get('order_id')}, urgency={result.get('urgency')}")

    # Update state with triage results
    state["intent"] = result.get("intent")
    state["urgency"] = result.get("urgency")

    # Initialize entities if not exists
    state.setdefault("entities", {})
    
    # Store extracted information
    state["entities"]["query"] = message
    
    if result.get("order_id"):
        state["entities"]["order_id"] = result["order_id"]
        logger.debug(f"Extracted order_id: {result['order_id']}")
    
    if "confidence" in result:
        state["entities"]["triage_confidence"] = result["confidence"]
    
    # Always store user_issue
    state["entities"]["user_issue"] = result.get("user_issue", message)

    # Create comprehensive triage summary for downstream agents
    triage_summary = f"""Triage Analysis Summary:
- Original Query: {message}
- User Issue: {result.get("user_issue", message)}
- Detected Intent: {result.get("intent")}
- Urgency Level: {result.get("urgency", "normal")}
- Order ID: {result.get("order_id") or "Not found"}
- Confidence Score: {result.get("confidence", 0.50)}
"""
    
    state["entities"]["triage_summary"] = triage_summary

    # Move to next state
    state["current_state"] = "DATA_FETCH"
    logger.info(f"🔄 TRIAGE: Moving to DATA_FETCH state")
    
    return state
