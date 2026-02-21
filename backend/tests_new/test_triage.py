"""
Tests for the triage agent:
  - extract_order_id
  - rule_based_intent
  - run_triage (unit, skips LLM via mocks where needed)
"""
import pytest
from app.agents.triage.agent import extract_order_id, rule_based_intent, run_triage


# ═══════════════════════════════════════════════════════════════════════════════
# 1. extract_order_id
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtractOrderId:
    """Order ID regex must find long numeric IDs in many message formats."""

    def test_bare_number(self):
        assert extract_order_id("296842434273") == "296842434273"

    def test_number_with_trailing_words(self):
        # The bug fix case: 3-word message that looks like a general reply
        assert extract_order_id("296842434273 this is") == "296842434273"

    def test_number_with_leading_words(self):
        assert extract_order_id("here it is 287899092720") == "287899092720"

    def test_order_id_prefix(self):
        assert extract_order_id("my order id is 12345") == "12345"

    def test_hash_prefix(self):
        assert extract_order_id("order #54321 please refund") == "54321"

    def test_order_hash_prefix(self):
        assert extract_order_id("order#98765 needs tracking") == "98765"

    def test_it_is_pattern(self):
        assert extract_order_id("it is 99988877766") == "99988877766"

    def test_no_number_returns_none(self):
        assert extract_order_id("hey hi how are you") is None

    def test_number_too_short_returns_none(self):
        # Only numbers with ≥ 5 digits are considered order IDs
        assert extract_order_id("call 1234") is None

    def test_five_digit_minimum(self):
        assert extract_order_id("order 10000") == "10000"

    def test_number_in_mid_sentence(self):
        assert extract_order_id("I placed order 777888999 yesterday") == "777888999"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. rule_based_intent
# ═══════════════════════════════════════════════════════════════════════════════

class TestRuleBasedIntent:

    # ── Greetings ────────────────────────────────────────────────────────────
    @pytest.mark.parametrize("msg", [
        "hi", "hey", "hello", "hey hi", "hey hii",
        "good morning", "good evening", "howdy", "greetings",
        "how are you", "what can you do", "help me",
    ])
    def test_greetings_are_general_question(self, msg):
        assert rule_based_intent(msg) == "general_question", (
            f"'{msg}' should be general_question"
        )

    # ── Short messages with no keywords ──────────────────────────────────────
    @pytest.mark.parametrize("msg", [
        "what now",               # 2 words, no keywords
        "296842434273 this is",   # 3-word bare order-ID reply
        "okay sure",              # generic 2-word
    ])
    def test_short_non_keyword_messages(self, msg):
        assert rule_based_intent(msg) == "general_question"

    # ── Informational queries → policy_info ──────────────────────────────────
    @pytest.mark.parametrize("msg", [
        "i want to know the refund policies",
        "i want to know the return policy",
        "tell me about your exchange policy",
        "what is your cancellation policy",
        "what are the refund rules",
        "can you explain the return rules",
        "information about refund",
        "details about cancellation",
    ])
    def test_informational_queries_are_policy_info(self, msg):
        assert rule_based_intent(msg) == "policy_info", (
            f"'{msg}' should be policy_info"
        )

    # ── Action intents ────────────────────────────────────────────────────────
    @pytest.mark.parametrize("msg, expected", [
        ("i want to return my order", "return"),
        ("send it back please", "return"),
        ("please refund my money", "refund"),
        ("get my money back", "refund"),
        ("cancel my order", "cancel"),
        ("want to cancel", "cancel"),
        ("exchange this for a different size", "exchange"),
        ("swap for a different color", "exchange"),
        ("where is my order", "order_tracking"),
        ("track my order status", "order_tracking"),
        ("check status of order", "order_tracking"),
        ("this product is terrible", "complaint"),
        ("very disappointed with it", "complaint"),
        ("the app is not working", "technical_issue"),
        ("there is a bug in the website", "technical_issue"),
    ])
    def test_action_intents(self, msg, expected):
        assert rule_based_intent(msg) == expected, (
            f"Expected '{expected}' for '{msg}'"
        )

    # ── Policy keywords ───────────────────────────────────────────────────────
    @pytest.mark.parametrize("msg", ["refund policy", "return policy", "exchange policy"])
    def test_policy_keywords(self, msg):
        assert rule_based_intent(msg) == "policy_info"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. run_triage (deterministic paths — no LLM)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunTriage:
    """
    run_triage short-circuits for general_question without calling the LLM.
    For other intents it calls Ollama; we only test the deterministic paths here.
    """

    def test_greeting_is_general_question(self):
        result = run_triage("hey hi")
        assert result["intent"] == "general_question"

    def test_greeting_order_id_is_none(self):
        result = run_triage("hello there")
        assert result["order_id"] is None

    def test_bare_order_id_reply_has_correct_order_id(self):
        """
        Critical fix: short-circuited general_question must still carry the order_id.
        Without this fix, awaiting_order_id flows break.
        """
        result = run_triage("296842434273 this is")
        assert result["order_id"] == "296842434273", (
            "Order ID must be extracted even when message is classified as general_question"
        )

    def test_order_id_in_trailing_words(self):
        result = run_triage("here it is 287899092720")
        assert result["order_id"] == "287899092720"

    def test_result_has_required_keys(self):
        result = run_triage("track my order 12345")
        for key in ("intent", "urgency", "order_id", "confidence", "user_issue"):
            assert key in result, f"Key '{key}' missing from triage result"

    def test_order_id_injected_in_full_sentence(self):
        result = run_triage("refund for order 54321 please")
        assert result["order_id"] == "54321"
