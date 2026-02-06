import json
import re

from app.orchestrator.guard import agent_guard
from app.agents.triage.prompts import TRIAGE_PROMPT

try:
    import ollama
except ImportError:
    ollama = None

INTENT_RULES = {
    "refund": ["refund", "money back"],
    "return": ["return"],
    "exchange": ["exchange", "replace"],
    "order_tracking": ["where is my order", "track", "order status"],
    "complaint": ["bad", "worst", "not happy", "angry"],
    "technical_issue": ["not working", "error", "bug"],
}

URGENT_WORDS = ["urgent", "now", "immediately", "asap"]


def extract_order_id(text: str) -> str | None:
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None


def rule_based_intent(text: str) -> str | None:
    for intent, words in INTENT_RULES.items():
        for word in words:
            if word in text:
                return intent
    return None


def rule_based_urgency(text: str) -> str | None:
    for word in URGENT_WORDS:
        if word in text:
            return "high"
    return None


def run_triage(message: str) -> dict:
    text = message.lower()
    order_id = extract_order_id(text)
    urgency = rule_based_urgency(text)

    if ollama is None:
        return {
            "intent": "unknown",
            "urgency": urgency or "normal",
            "order_id": order_id,
            "confidence": 0.50,
        }

    prompt = TRIAGE_PROMPT.format(message=message)
    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}],
    )

    output = response.get("message", {}).get("content", "")

    try:
        result = json.loads(output)
        result["order_id"] = result.get("order_id") or order_id
        if not result.get("urgency"):
            result["urgency"] = urgency or "normal"
        if not result.get("confidence"):
            result["confidence"] = 0.50
        # Ensure user_issue is always present
        if not result.get("user_issue"):
            result["user_issue"] = message
        return result
    except (ValueError, TypeError):
        return {
            "intent": "unknown",
            "urgency": urgency or "normal",
            "order_id": order_id,
            "confidence": 0.50,
            "user_issue": message,
        }


@agent_guard("triage")
async def triage_agent(state):
    message = state.get("user_message") or ""
    result = run_triage(message)

    state["intent"] = result.get("intent")
    state["urgency"] = result.get("urgency")

    state.setdefault("entities", {})
    state["entities"]["query"] = message
    if result.get("order_id"):
        state["entities"]["order_id"] = result["order_id"]
    if "confidence" in result:
        state["entities"]["triage_confidence"] = result["confidence"]
    # Always store user_issue
    state["entities"]["user_issue"] = result.get("user_issue", message)

    # Create comprehensive triage summary query for downstream agents
    triage_summary = f"""Triage Analysis Summary:
- Original Query: {message}
- User Issue: {result.get("user_issue", message)}
- Detected Intent: {result.get("intent")}
- Urgency Level: {result.get("urgency", "normal")}
- Order ID: {result.get("order_id") or "Not found"}
- Confidence Score: {result.get("confidence", 0.50)}
- Full Response: intent={{intent}}, urgency={{urgency}}, order_id={{order_id}}, confidence={{confidence}}, user_issue={{user_issue}}""".format(
        intent=result.get("intent"),
        urgency=result.get("urgency", "normal"),
        order_id=result.get("order_id") or "null",
        confidence=result.get("confidence", 0.50),
        user_issue=result.get("user_issue", message)
    )
    
    state["entities"]["triage_summary"] = triage_summary

    state["current_state"] = "DATA_FETCH"
    return state
