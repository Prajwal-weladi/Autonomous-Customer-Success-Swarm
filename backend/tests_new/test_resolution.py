"""
Tests for the resolution agent:
  - All response generator functions (refund, return, exchange, cancel, tracking,
    complaint, technical_issue, general_question)
  - resolution_agent state machine (confirmation gate, full completion, unknown intent)
"""
import pytest
from datetime import datetime, timedelta
from app.agents.resolution.agent import (
    generate_refund_response,
    generate_return_response,
    generate_exchange_response,
    generate_cancellation_response,
    generate_tracking_response,
    generate_complaint_response,
    generate_technical_issue_response,
    generate_general_response,
    resolution_agent,
)


def days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def base_state(intent: str, order_details: dict, policy_allowed: bool,
               confirmation_status: str = None) -> dict:
    entities = {
        "order_details": order_details,
        "policy_result": {
            "allowed": policy_allowed,
            "reason": "eligible" if policy_allowed else "not eligible",
            "policy_checked": True,
        },
    }
    if confirmation_status:
        entities["confirmation_status"] = confirmation_status
    return {"intent": intent, "entities": entities, "current_state": "RESOLUTION"}


ORDER = {
    "order_id": "12345",
    "product": "Wireless Headphones",
    "status": "Delivered",
    "order_date": days_ago(20),
    "delivered_date": days_ago(10),
    "amount": 2199,
}

SHIPPED_ORDER = {
    "order_id": "67890",
    "product": "Laptop Bag",
    "status": "Shipped",
    "order_date": days_ago(3),
    "delivered_date": None,
    "amount": 1299,
}


# ═══════════════════════════════════════════════════════════════════════════════
# Response generators  (pure functions — no async)
# ═══════════════════════════════════════════════════════════════════════════════

class TestResponseGenerators:

    def _state(self, allowed: bool, order=None) -> dict:
        return {
            "entities": {
                "order_details": order or ORDER,
                "policy_result": {"allowed": allowed, "reason": "test"},
            }
        }

    # ── Refund ────────────────────────────────────────────────────────────────
    def test_refund_approved_contains_order_id(self):
        reply = generate_refund_response(self._state(True))
        assert "12345" in reply

    def test_refund_approved_mentions_days(self):
        reply = generate_refund_response(self._state(True))
        assert "5-7 business days" in reply

    def test_refund_denied_contains_reason(self):
        state = {"entities": {"order_details": ORDER, "policy_result": {"allowed": False, "reason": "Window expired"}}}
        reply = generate_refund_response(state)
        assert "Window expired" in reply

    # ── Return ────────────────────────────────────────────────────────────────
    def test_return_approved_contains_order_id(self):
        reply = generate_return_response(self._state(True))
        assert "12345" in reply

    def test_return_approved_mentions_label(self):
        reply = generate_return_response(self._state(True))
        assert "label" in reply.lower()

    def test_return_denied_contains_reason(self):
        state = {"entities": {"order_details": ORDER, "policy_result": {"allowed": False, "reason": "Already 60 days"}}}
        reply = generate_return_response(state)
        assert "Already 60 days" in reply

    # ── Exchange ──────────────────────────────────────────────────────────────
    def test_exchange_approved_contains_order_id(self):
        reply = generate_exchange_response(self._state(True))
        assert "12345" in reply

    def test_exchange_denied(self):
        state = {"entities": {"order_details": ORDER, "policy_result": {"allowed": False, "reason": "Policy expired"}}}
        reply = generate_exchange_response(state)
        assert "cannot" in reply.lower() or "sorry" in reply.lower()

    # ── Cancellation ──────────────────────────────────────────────────────────
    def test_cancel_success_for_processing(self):
        order = {**ORDER, "status": "Processing", "delivered_date": None}
        state = {"entities": {"order_details": order, "policy_result": {"allowed": True, "reason": "ok"}}}
        reply = generate_cancellation_response(state)
        assert "cancelled" in reply.lower()
        assert "12345" in reply

    def test_cancel_denied_already_shipped(self):
        order = {**ORDER, "status": "Shipped", "delivered_date": None}
        state = {"entities": {"order_details": order, "policy_result": {"allowed": False, "reason": "shipped"}}}
        reply = generate_cancellation_response(state)
        assert "shipped" in reply.lower()

    def test_cancel_already_cancelled(self):
        order = {**ORDER, "status": "Cancelled", "delivered_date": None}
        state = {"entities": {"order_details": order, "policy_result": {"allowed": False, "reason": "already cancelled"}}}
        reply = generate_cancellation_response(state)
        assert "already been cancelled" in reply.lower()

    def test_cancel_no_order_details(self):
        state = {"entities": {"order_details": None, "policy_result": {}}}
        reply = generate_cancellation_response(state)
        assert "couldn't find" in reply.lower() or "not found" in reply.lower() or "verify" in reply.lower()

    # ── Tracking ──────────────────────────────────────────────────────────────
    def test_tracking_delivered_order(self):
        state = {"entities": {"order_details": ORDER}}
        reply = generate_tracking_response(state)
        assert "delivered" in reply.lower()
        assert "12345" in reply

    def test_tracking_shipped_order(self):
        state = {"entities": {"order_details": SHIPPED_ORDER}}
        reply = generate_tracking_response(state)
        assert "transit" in reply.lower() or "shipped" in reply.lower()

    def test_tracking_no_order_details(self):
        state = {"entities": {"order_details": None}}
        reply = generate_tracking_response(state)
        assert "couldn't find" in reply.lower() or "not found" in reply.lower() or "verify" in reply.lower()

    # ── Complaint ─────────────────────────────────────────────────────────────
    def test_complaint_with_order(self):
        state = {"entities": {"order_details": ORDER, "user_issue": "product broke"}}
        reply = generate_complaint_response(state)
        assert "12345" in reply

    def test_complaint_without_order(self):
        state = {"entities": {"order_details": None, "user_issue": "bad service"}}
        reply = generate_complaint_response(state)
        assert isinstance(reply, str) and len(reply) > 10

    # ── Technical issue ───────────────────────────────────────────────────────
    def test_technical_issue_response(self):
        state = {"entities": {}}
        reply = generate_technical_issue_response(state)
        assert "technical" in reply.lower() or "support" in reply.lower()

    # ── General ───────────────────────────────────────────────────────────────
    def test_general_response(self):
        state = {"entities": {"user_issue": "just saying hi"}}
        reply = generate_general_response(state)
        assert isinstance(reply, str) and len(reply) > 10


# ═══════════════════════════════════════════════════════════════════════════════
# resolution_agent state machine
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestResolutionAgent:

    async def test_refund_confirmed_completes(self):
        state = base_state("refund", ORDER, True, confirmation_status="confirmed")
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"
        assert result["status"] == "completed"
        assert "12345" in result["reply"]

    async def test_refund_unconfirmed_asks_for_confirmation(self):
        state = base_state("refund", ORDER, True)  # no confirmation_status
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"
        assert "sure" in result["reply"].lower() or "confirm" in result["reply"].lower()
        assert result["entities"].get("action") == "CONFIRMATION_REQUIRED"

    async def test_return_confirmed_completes(self):
        state = base_state("return", ORDER, True, confirmation_status="confirmed")
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"
        assert result["status"] == "completed"

    async def test_exchange_confirmed_completes(self):
        state = base_state("exchange", ORDER, True, confirmation_status="confirmed")
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"

    async def test_cancel_confirmed_completes(self):
        processing_order = {**ORDER, "status": "Processing", "delivered_date": None}
        state = base_state("cancel", processing_order, True, confirmation_status="confirmed")
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"

    async def test_order_tracking_completes_without_confirmation(self):
        """Tracking does not require confirmation."""
        state = base_state("order_tracking", ORDER, True)
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"
        assert "12345" in result["reply"]

    async def test_complaint_completes(self):
        state = {**base_state("complaint", ORDER, True), "entities": {
            "order_details": ORDER, "user_issue": "broken product",
            "policy_result": {"allowed": True, "reason": "ok"},
        }}
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"

    async def test_technical_issue_completes(self):
        state = base_state("technical_issue", None, True)
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"

    async def test_general_question_completes(self):
        state = {**base_state("general_question", None, True), "entities": {
            "order_details": None, "user_issue": "just asking",
            "policy_result": {"allowed": True, "reason": "ok"},
        }}
        result = await resolution_agent(state)
        assert result["current_state"] == "COMPLETED"

    async def test_unknown_intent_handoff(self):
        state = base_state("unknown_gibberish", None, False)
        result = await resolution_agent(state)
        assert result["current_state"] == "HUMAN_HANDOFF"

    async def test_reply_is_set_on_all_known_intents(self):
        for intent in ("order_tracking", "complaint", "technical_issue", "general_question"):
            order = ORDER if intent == "order_tracking" else None
            state = {
                "intent": intent,
                "entities": {
                    "order_details": order,
                    "policy_result": {"allowed": True, "reason": "ok"},
                    "user_issue": "test",
                },
                "current_state": "RESOLUTION",
            }
            result = await resolution_agent(state)
            assert "reply" in result and result["reply"], f"No reply for intent='{intent}'"

    async def test_action_entity_set_after_completion(self):
        state = base_state("order_tracking", ORDER, True)
        result = await resolution_agent(state)
        assert result["entities"].get("action") == "ORDER_TRACKING"

    async def test_confirmation_cleared_after_action(self):
        state = base_state("refund", ORDER, True, confirmation_status="confirmed")
        result = await resolution_agent(state)
        assert "confirmation_status" not in result["entities"]
