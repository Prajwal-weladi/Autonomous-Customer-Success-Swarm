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
    "refund": ["refund", "money back", "get my money", "cancel", "cancel order"],
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


def safe_json_parse(output: str) -> Dict[str, Any] | None:
    try:
        output = output.strip()
        if "```" in output:
            output = output.split("```")[1].strip()
        return json.loads(output)
    except Exception as e:
        logger.error(f"JSON parsing failed: {e}")
        return None


# --------------------------------------------------
# Hybrid Triage Logic
# --------------------------------------------------
def run_triage(message: str) -> Dict[str, Any]:

    order_id = extract_order_id(message)
    fallback_intent = rule_based_intent(message)
    fallback_urgency = rule_based_urgency(message)

    if not OLLAMA_AVAILABLE:
        return {
            "intent": fallback_intent,
            "urgency": fallback_urgency,
            "order_id": order_id,
            "confidence": 0.60,
            "user_issue": message
        }

    try:
        prompt = TRIAGE_PROMPT.format(message=message)

        response = ollama.chat(
            model="mistral:instruct",
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

    except Exception as e:
        logger.error(f"LLM triage failed: {e}")
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
async def triage_agent(state: Dict[str, Any]) -> Dict[str, Any]:

    logger.info("Processing new triage request")

    message = state.get("user_message", "").strip()

    if not message:
        state["reply"] = "Please provide your request."
        state["current_state"] = "WAITING_FOR_INFO"
        return state

    result = run_triage(message)

    intent = result["intent"]
    urgency = result["urgency"]
    order_id = result.get("order_id")
    confidence = result["confidence"]

    state["intent"] = intent
    state["urgency"] = urgency
    state.setdefault("entities", {})
    state["entities"].update({
        "query": message,
        "user_issue": result["user_issue"],
        "triage_confidence": confidence
    })

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
    return state
