import json
import re
import ollama
from prompts import TRIAGE_PROMPT

# ----------------------------
# Keyword Rules
# ----------------------------

INTENT_RULES = {
    "refund": ["refund", "money back"],
    "return": ["return"],
    "exchange": ["exchange", "replace"],
    "order_tracking": ["where is my order", "track", "order status"],
    "complaint": ["bad", "worst", "not happy", "angry"],
    "technical_issue": ["not working", "error", "bug"]
}

URGENT_WORDS = ["urgent", "now", "immediately", "asap"]

# ----------------------------
# Utility Functions
# ----------------------------

def extract_order_id(text):
    match = re.search(r"\b\d{4,}\b", text)
    return match.group() if match else None


def rule_based_intent(text):
    for intent, words in INTENT_RULES.items():
        for w in words:
            if w in text:
                return intent
    return None


def rule_based_urgency(text):
    for w in URGENT_WORDS:
        if w in text:
            return "high"
    return None

# ----------------------------
# Main Triage Function
# ----------------------------

def run_triage(message: str):

    text = message.lower()

    order_id = extract_order_id(text)
    intent = rule_based_intent(text)
    urgency = rule_based_urgency(text)

    # If rules caught intent, return fast result
    if intent:
        return {
            "intent": intent,
            "urgency": urgency or "normal",
            "order_id": order_id,
            "confidence": 0.85
        }

    # ---------- LLM Fallback ----------

    prompt = TRIAGE_PROMPT.format(message=message)

    response = ollama.chat(
        model="llama3",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    output = response["message"]["content"]

    try:
        result = json.loads(output)
        result["order_id"] = result.get("order_id") or order_id
        return result

    except:
        return {
            "intent": "unknown",
            "urgency": "normal",
            "order_id": order_id,
            "confidence": 0.50
        }
