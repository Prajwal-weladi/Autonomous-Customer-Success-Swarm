"""
Configuration and constants for the triage agent.
"""

# Short greetings / chitchat that should always be general_question
GREETING_PHRASES = [
    "hi", "hey", "hello", "hey hi", "hi there", "hello there", "good morning",
    "good afternoon", "good evening", "howdy", "greetings", "sup", "what's up",
    "how are you", "how can you help", "what can you do", "help me", "help",
]

INTENT_RULES = {
    "list_orders": ["list my orders", "my orders", "show orders", "all orders", "recent orders", "my history", "what did i buy", "show my purchases", "order history", "show my order history", "list all", "purchased by me", "list", "purchased", "all my order", "bought"],
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
    "order_tracking": ["where is my order", "track", "order status", "hasn't arrived", "not received", "check status", "check my order", "status of order", "status for order", "the status", "give me the status", "check the status", "status", "check status", "where is #", "latest update", "order details", "info of my order"],
    "complaint": ["bad", "worst", "terrible", "not happy", "angry", "disappointed", "poor quality"],
    "technical_issue": ["not working", "error", "bug", "broken", "defective"],
}

URGENT_WORDS = ["urgent", "now", "immediately", "asap", "emergency", "right now"]

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

# LLM Configuration
LLM_MODEL = "qwen2.5:0.5b"
LLM_TEMPERATURE = 0.1

# Confidence Thresholds
DEFAULT_CONFIDENCE = 0.70
FALLBACK_CONFIDENCE = 0.50
RULE_BASED_CONFIDENCE = 0.60

