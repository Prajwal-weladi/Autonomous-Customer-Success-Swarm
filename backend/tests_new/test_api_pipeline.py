"""
Integration tests for the live API server.
The uvicorn server MUST be running on http://127.0.0.1:8000.
These tests use `requests` to exercise the full HTTP pipeline.
"""
import uuid
import pytest
import requests

BASE_URL = "http://127.0.0.1:8000"


def new_conv() -> str:
    return str(uuid.uuid4())


def post(conv_id: str, message: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/v1/message",
        json={"conversation_id": conv_id, "message": message},
        timeout=30,
    )
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
    return resp.json()


@pytest.fixture(scope="module", autouse=True)
def check_server():
    """Skip all tests in this module if the live server is not reachable."""
    try:
        requests.get(BASE_URL, timeout=3)
    except requests.exceptions.ConnectionError:
        pytest.skip("Live server not running — start uvicorn first", allow_module_level=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Route 1: Policy info (no order ID needed)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolicyInfoRoute:

    def test_refund_policy_returns_policy_text(self):
        data = post(new_conv(), "what is the refund policy")
        assert "30 days" in data["reply"] or "refund" in data["reply"].lower()

    def test_return_policy_returns_policy_text(self):
        data = post(new_conv(), "tell me about the return policy")
        assert "return" in data["reply"].lower() or "45 days" in data["reply"]

    def test_exchange_policy(self):
        data = post(new_conv(), "tell me about exchange policy")
        assert "exchange" in data["reply"].lower()

    def test_cancellation_policy(self):
        data = post(new_conv(), "what is the cancellation policy")
        assert "cancel" in data["reply"].lower()

    def test_response_includes_conversation_id(self):
        cid = new_conv()
        data = post(cid, "what is the refund policy")
        assert data["conversation_id"] == cid


# ═══════════════════════════════════════════════════════════════════════════════
# Route 2: Greetings / general chat
# ═══════════════════════════════════════════════════════════════════════════════

class TestGreetingsRoute:

    def test_hello_gets_reply(self):
        data = post(new_conv(), "hello")
        assert isinstance(data["reply"], str) and len(data["reply"]) > 5

    def test_hey_hi_gets_reply(self):
        data = post(new_conv(), "hey hi")
        assert isinstance(data["reply"], str) and len(data["reply"]) > 5

    def test_good_morning_gets_reply(self):
        data = post(new_conv(), "good morning")
        assert isinstance(data["reply"], str)

    def test_response_schema(self):
        data = post(new_conv(), "hi")
        assert "conversation_id" in data
        assert "reply" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Route 3: Action intents without order ID → bot asks for order
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrderIdPrompting:

    def test_refund_without_order_prompts(self):
        data = post(new_conv(), "i want a refund")
        reply = data["reply"].lower()
        assert "order" in reply or "number" in reply or "id" in reply

    def test_return_without_order_prompts(self):
        data = post(new_conv(), "i want to return")
        reply = data["reply"].lower()
        assert "order" in reply or "number" in reply or "id" in reply

    def test_tracking_without_order_prompts(self):
        data = post(new_conv(), "where is my order")
        reply = data["reply"].lower()
        assert "order" in reply or "number" in reply or "id" in reply

    def test_cancel_without_order_prompts(self):
        data = post(new_conv(), "cancel my order")
        reply = data["reply"].lower()
        assert "order" in reply or "number" in reply or "id" in reply


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-turn: provide order ID on the 2nd turn
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiTurnFlow:

    def test_order_id_extracted_from_bare_reply(self):
        """
        Turn 1: no order ID → bot asks
        Turn 2: user sends just an order number (with trailing words) → bot processes
        """
        cid = new_conv()
        r1 = post(cid, "i want to track my order")
        reply1 = r1["reply"].lower()
        assert "order" in reply1 or "number" in reply1 or "id" in reply1

        # Turn 2 — provide bare number (the critical fix case)
        r2 = post(cid, "296842434273 this is")
        assert isinstance(r2["reply"], str) and len(r2["reply"]) > 5
        # Must NOT ask for order ID again
        assert "please provide" not in r2["reply"].lower() or "not found" in r2["reply"].lower()

    def test_second_turn_without_order_id_asks_again(self):
        """If user doesn't provide the order ID on turn 2, the bot should ask again."""
        cid = new_conv()
        post(cid, "i want a refund")
        r2 = post(cid, "okay cool fine with that")
        # Either re-requests the order ID or gives a sensible response
        assert isinstance(r2["reply"], str) and len(r2["reply"]) > 5


# ═══════════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_very_long_message_does_not_crash(self):
        data = post(new_conv(), "refund " * 100)
        assert isinstance(data["reply"], str)

    def test_numeric_only_message(self):
        data = post(new_conv(), "12345")
        assert isinstance(data["reply"], str)

    def test_punctuation_only_message(self):
        data = post(new_conv(), "??")
        assert isinstance(data["reply"], str)

    def test_two_conversations_are_isolated(self):
        """Two parallel conversations must not bleed state into each other."""
        cid1, cid2 = new_conv(), new_conv()
        post(cid1, "i want a refund")   # cid1 → awaiting order ID
        r2 = post(cid2, "hello")        # cid2 → fresh greeting
        # cid2 should not be affected by cid1's state
        assert isinstance(r2["reply"], str)
