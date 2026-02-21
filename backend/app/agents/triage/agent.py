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

# Short greetings / chitchat that should always be general_question
GREETING_PHRASES = [
    "hi", "hey", "hello", "hey hi", "hi there", "hello there", "good morning",
    "good afternoon", "good evening", "howdy", "greetings", "sup", "what's up",
    "how are you", "how can you help", "what can you do", "help me", "help",
]

INTENT_RULES = {
    "policy_info": [
        "policy", "policies",
        "refund policy", "return policy", "exchange policy",
        "cancellation policy", "cancel policy",
        "how does", "what is your", "tell me about", "what are the",
        "explain", "want to know", "like to know", "know about",
        "about refund", "about return", "about exchange", "about cancel",
        "for refund", "for return", "for exchange",
        "refund rules", "return rules", "cancellation rules",
    ],
    "cancel": ["cancel order", "cancel my order", "cancel this order", "want to cancel"],
    "refund": ["refund", "money back", "get my money"],
    "return": ["return", "send back", "send it back", "don't want"],
    "exchange": ["exchange", "replace", "swap", "different size", "different color"],
    "order_tracking": ["where is my order", "track", "order status", "hasn't arrived", "not received", "check status", "check my order", "status of order", "status for order"],
    "complaint": ["bad", "worst", "terrible", "not happy", "angry", "disappointed", "poor quality"],
    "technical_issue": ["not working", "error", "bug", "broken", "defective"],
}

URGENT_WORDS = ["urgent", "now", "immediately", "asap", "emergency", "right now"]


def extract_order_id(text: str) -> str | None:
    """Extract order ID from various natural language patterns"""
    
    # Pattern 1: "order id is 12345" / "order id: 12345" / "order id 12345"
    match = re.search(r'order\s*id\s*(?:is|:)?\s*#?(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: "my id is 12345" / "id is 12345" / "id: 12345"
    match = re.search(r'\bid\s*(?:is|:)?\s*#?(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 3: "order 12345" / "order #12345"
    match = re.search(r'order\s*#?(\d+)', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 4: "#12345"
    match = re.search(r'#(\d+)', text)
    if match:
        return match.group(1)

    # Pattern 5: "it's 12345" / "it is 12345" / "the number is 12345"
    match = re.search(r"(?:it'?s|it is|number is|is)\s+#?(\d{4,})", text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 6: bare long number (5+ digits) — likely an order ID
    match = re.search(r'\b(\d{5,})\b', text)
    if match:
        return match.group(1)

    return None


# Info-seeking phrases — if paired with any action topic, route to policy_info
INFO_SEEKING_PHRASES = [
    "want to know", "like to know", "know about", "know the",
    "tell me", "explain", "what is", "what are", "how does", "how do",
    "can you tell", "information about", "info about", "details about",
    "learn about", "understand",
]

# Topic words that, when paired with an info-seeking phrase, signal a policy query
ACTION_TOPIC_WORDS = [
    "refund", "return", "exchange", "cancel", "cancellation",
    "policy", "policies", "rules",
]


def rule_based_intent(text: str) -> str | None:
    """Determine intent using keyword matching"""
    text_lower = text.lower().strip()

    # Check for greetings first — they must never be action intents
    for phrase in GREETING_PHRASES:
        if text_lower == phrase or text_lower.startswith(phrase + " ") or text_lower.endswith(" " + phrase):
            return "general_question"

    # Also treat very short messages (≤ 3 words) with no clear support keyword as general_question
    words = text_lower.split()
    if len(words) <= 3 and not any(
        kw in text_lower
        for keywords in INTENT_RULES.values()
        for kw in keywords
    ):
        return "general_question"

    # Informational query override:
    # If the message has info-seeking language AND an action topic, it's a policy question —
    # not an action request. This prevents "i want to know the refund policy" → refund.
    has_info_seeking = any(phrase in text_lower for phrase in INFO_SEEKING_PHRASES)
    has_action_topic = any(word in text_lower for word in ACTION_TOPIC_WORDS)
    if has_info_seeking and has_action_topic:
        return "policy_info"

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


def run_triage(message: str, history: list | None = None) -> dict:
    """
    Main triage function that analyzes user message.
    Uses LLM if available, falls back to rules.

    Args:
        message: The current user message.
        history: Optional list of prior turns as [{"role": "user"|"assistant", "content": "..."}, ...]
    """
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    
    logger.info(f"🔍 TRIAGE: Analyzing message: '{message[:100]}...'")

    # Build history string for the prompt
    history_text = ""
    if history:
        lines = []
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        history_text = "\n".join(lines)

    # For rule-based extraction also consider prior context (e.g. bare order ID reply)
    full_context = f"{history_text}\n{message}" if history_text else message

    text = full_context.lower()
    order_id = extract_order_id(message) or extract_order_id(full_context)
    urgency = rule_based_urgency(text)

    # ── Check the CURRENT message alone for greeting/general classification ──
    # This must run before the LLM so it cannot be overridden.
    message_intent = rule_based_intent(message)
    if message_intent == "general_question":
        # Still include the order_id if one was found in the message
        # (e.g. "296842434273 this is" — 3 words, no keywords → general_question,
        #  but the number IS an order ID we need to pass along)
        logger.info("⚡ TRIAGE: Message detected as greeting/general — skipping LLM, returning general_question")
        return {
            "intent": "general_question",
            "urgency": "normal",
            "order_id": order_id,   # ← use the extracted value, not None
            "confidence": 0.90,
            "user_issue": message,
        }
    # ────────────────────────────────────────────────────────────────────────

    fallback_intent = message_intent or rule_based_intent(text) or "unknown"

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
        prompt = TRIAGE_PROMPT.format(message=message, history=history_text or "(no prior history)")
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

    # ─── SPECIAL CASE: we were waiting for the user to provide an order ID ───
    # In this case do NOT re-run full triage — just extract the order ID from
    # the reply and keep the intent that was already established.
    if state.get("awaiting_order_id") and state.get("intent"):
        order_id = extract_order_id(message)
        if order_id:
            logger.info(
                f"📦 TRIAGE: 'awaiting_order_id' reply — keeping intent='{state['intent']}', "
                f"extracted order_id={order_id}"
            )
            state.setdefault("entities", {})
            state["entities"]["order_id"] = order_id
            state["entities"]["query"] = message
            state["awaiting_order_id"] = False
            state["current_state"] = "DATA_FETCH"
            return state
        else:
            # User replied but there's still no order ID — ask again
            logger.warning("⚠️ TRIAGE: Awaiting order ID but none found in reply")
            state["reply"] = "I couldn't find an order ID in your message. Could you please share your order number?"
            state["current_state"] = "COMPLETED"
            return state
    # ─────────────────────────────────────────────────────────────────────────

    # Normal triage path
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
