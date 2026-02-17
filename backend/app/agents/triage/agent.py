import json
import re
import logging
from typing import Dict, Any

from app.orchestrator.guard import agent_guard
from app.agents.triage.prompts import TRIAGE_PROMPT

# --------------------------------------------------
# Logging Configuration
# --------------------------------------------------
logger = logging.getLogger("triage_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# --------------------------------------------------
# Optional Ollama Import
# --------------------------------------------------
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama not available. Falling back to rule-based triage.")


# --------------------------------------------------
# Rule-Based Intent & Urgency
# --------------------------------------------------
INTENT_RULES = {
    "policy_info": ["policy", "refund policy", "return policy", "exchange policy", "cancellation policy", "cancel policy", "how does", "what is your", "tell me about", "what are the", "explain"],
    "cancel": ["cancel order", "cancel my order", "cancel this order", "want to cancel"],
    "refund": ["refund", "money back", "get my money"],
    "return": ["return", "send back", "don't want"],
    "exchange": ["exchange", "replace", "swap"],
    "order_tracking": ["where is my order", "track", "order status"],
    "complaint": ["bad", "worst", "terrible", "angry"],
    "technical_issue": ["not working", "error", "bug", "broken"],
}

URGENT_WORDS = ["urgent", "now", "immediately", "asap", "right now"]


# --------------------------------------------------
# Utility Functions
# --------------------------------------------------
def extract_order_id(text: str) -> str | None:
    match = re.search(r"(?:order\s*)?id\s*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)

    match = re.search(r"order\s*(\d+)", text, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def rule_based_intent(text: str) -> str:
    text_lower = text.lower()

    # 🔹 Detect policy / informational queries FIRST
    if any(word in text_lower for word in ["policy", "policies", "rules", "how does", "what is", "what are"]):
        return "general_question"

    # 🔹 Then detect operational intents
    for intent, keywords in INTENT_RULES.items():
        if any(keyword in text_lower for keyword in keywords):
            return intent

    return "general_question"



def rule_based_urgency(text: str) -> str:
    text_lower = text.lower()
    if any(word in text_lower for word in URGENT_WORDS):
        return "high"
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

    if not OLLAMA_AVAILABLE:
        logger.warning("⚠️ TRIAGE: Ollama not available, using rule-based analysis only")
        return {
            "intent": fallback_intent,
            "urgency": fallback_urgency,
            "order_id": order_id,
            "confidence": 0.60,
            "user_issue": message
        }

    try:
        logger.debug("Attempting LLM-based triage analysis")
        prompt = TRIAGE_PROMPT.format(message=message)

        response = ollama.chat(
            model="qwen2.5:0.5b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )

        parsed = safe_json_parse(response.get("message", {}).get("content", ""))

        if not parsed:
            raise ValueError("Invalid JSON from LLM")

        parsed["order_id"] = parsed.get("order_id") or order_id
        parsed["intent"] = parsed.get("intent") or fallback_intent
        parsed["urgency"] = parsed.get("urgency") or fallback_urgency
        parsed["confidence"] = parsed.get("confidence", 0.75)
        parsed["user_issue"] = parsed.get("user_issue", message)

        return parsed

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
            "urgency": fallback_urgency,
            "order_id": order_id,
            "confidence": 0.50,
            "user_issue": message
        }


# --------------------------------------------------
# Main Triage Agent
# --------------------------------------------------
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

    result = run_triage(message)
    logger.info(f"✅ TRIAGE: Detected intent={result.get('intent')}, order_id={result.get('order_id')}, urgency={result.get('urgency')}")

    intent = result["intent"]
    urgency = result["urgency"]
    order_id = result.get("order_id")
    confidence = result["confidence"]

    state["intent"] = intent
    state["urgency"] = urgency
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

    if order_id:
        state["entities"]["order_id"] = order_id

    # --------------------------------------------------
    # 1. General Conversational Handling
    # --------------------------------------------------
    if intent in ["general_question", "unknown"]:
        if OLLAMA_AVAILABLE:
            from app.agents.triage.prompts import CHAT_PROMPT

            chat_prompt = CHAT_PROMPT.format(message=message)

            response = ollama.chat(
                model="mistral:instruct",
                messages=[{"role": "user", "content": chat_prompt}],
                options={"temperature": 0.3}
            )

            state["reply"] = response.get("message", {}).get("content", "").strip()
        else:
            state["reply"] = "I'm here to help. Could you provide more details?"

        state["current_state"] = "COMPLETED"
        return state

    # --------------------------------------------------
    # 2. Ask for Order ID ONLY if required
    # --------------------------------------------------
    order_required_intents = ["refund", "return", "exchange", "order_tracking"]

    if intent in order_required_intents and not order_id:

        if OLLAMA_AVAILABLE:
            clarification_prompt = f"""
You are a professional customer support assistant.

The user wants to {intent}, but did not provide an order ID.
Politely ask them to provide their order ID.
"""

            try:
                response = ollama.chat(
                    model="mistral:instruct",
                    messages=[{"role": "user", "content": clarification_prompt}],
                    options={"temperature": 0.3}
                )

                state["reply"] = response.get("message", {}).get("content", "").strip()

            except Exception:
                state["reply"] = "To assist you with this request, could you please provide your order ID?"
        else:
            state["reply"] = "To assist you with this request, could you please provide your order ID?"

        state["current_state"] = "WAITING_FOR_INFO"
        return state

    # --------------------------------------------------
    # 3. Complaint / Technical without ID
    # --------------------------------------------------
    if intent in ["complaint", "technical_issue"] and not order_id:

        if OLLAMA_AVAILABLE:
            complaint_prompt = f"""
You are a helpful and empathetic customer support assistant.

The user is reporting a {intent}.
Respond empathetically and ask them to provide their order ID
or additional details about the issue.
"""

            try:
                response = ollama.chat(
                    model="mistral:instruct",
                    messages=[{"role": "user", "content": complaint_prompt}],
                    options={"temperature": 0.3}
                )

                state["reply"] = response.get("message", {}).get("content", "").strip()

            except Exception:
                state["reply"] = (
                    "I'm sorry to hear that. Could you please share your order ID "
                    "or provide more details about the issue?"
                )
        else:
            state["reply"] = (
                "I'm sorry to hear that. Could you please share your order ID "
                "or provide more details about the issue?"
            )

        state["current_state"] = "WAITING_FOR_INFO"
        return state

    # --------------------------------------------------
    # 4. Route Only When Ready
    # --------------------------------------------------
    state["current_state"] = "DATA_FETCH"
    logger.info(f"🔄 TRIAGE: Moving to DATA_FETCH state")
    
    return state
