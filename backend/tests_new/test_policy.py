"""
Tests for the policy agent:
  - get_policy_information   (informational queries, no order needed)
  - check_refund_policy      (30-day window, Delivered status)
  - check_return_policy      (45-day window, Delivered status)
  - check_exchange_policy    (same as return)
  - policy_agent state machine  (all intents routed correctly)
"""
import pytest
from datetime import datetime, timedelta
from app.agents.policy.agent import (
    get_policy_information,
    check_refund_policy,
    check_return_policy,
    check_exchange_policy,
    policy_agent,
)


def days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


# ═══════════════════════════════════════════════════════════════════════════════
# get_policy_information
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPolicyInformation:

    def test_refund_policy(self):
        result = get_policy_information("refund")
        assert result["policy_type"] == "refund"
        assert "30 days" in result["message"]

    def test_return_policy(self):
        result = get_policy_information("return")
        assert result["policy_type"] == "return"
        assert "45 days" in result["message"]

    def test_exchange_policy(self):
        result = get_policy_information("exchange")
        assert result["policy_type"] == "exchange"
        assert "exchange" in result["message"].lower()

    def test_cancel_policy(self):
        result = get_policy_information("cancel")
        assert result["policy_type"] == "cancel"
        assert "cancel" in result["message"].lower()

    def test_unknown_type_returns_all_policies(self):
        result = get_policy_information("unknown_type")
        assert result["policy_type"] == "all"
        assert "Refund" in result["message"]
        assert "Return" in result["message"]

    def test_no_type_returns_all_policies(self):
        result = get_policy_information(None)
        assert result["policy_type"] == "all"

    def test_message_is_string(self):
        for ptype in ("refund", "return", "exchange", "cancel", None):
            result = get_policy_information(ptype)
            assert isinstance(result["message"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# check_refund_policy  (30-day window)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckRefundPolicy:

    def test_eligible_recent_delivery(self):
        order = {"status": "Delivered", "delivered_date": days_ago(10)}
        result = check_refund_policy(order)
        assert result["allowed"] is True

    def test_ineligible_expired_window(self):
        order = {"status": "Delivered", "delivered_date": days_ago(35)}
        result = check_refund_policy(order)
        assert result["allowed"] is False
        assert "expired" in result["reason"].lower()

    def test_ineligible_not_delivered_shipped(self):
        order = {"status": "Shipped", "delivered_date": None}
        result = check_refund_policy(order)
        assert result["allowed"] is False
        assert "Shipped" in result["reason"]

    def test_ineligible_not_delivered_processing(self):
        order = {"status": "Processing", "delivered_date": None}
        result = check_refund_policy(order)
        assert result["allowed"] is False

    def test_ineligible_cancelled(self):
        order = {"status": "Cancelled", "delivered_date": None}
        result = check_refund_policy(order)
        assert result["allowed"] is False

    def test_no_delivered_date(self):
        order = {"status": "Delivered", "delivered_date": None}
        result = check_refund_policy(order)
        assert result["allowed"] is False
        assert "date" in result["reason"].lower()

    def test_empty_order_details(self):
        result = check_refund_policy(None)
        assert result["allowed"] is False

    def test_result_has_allowed_and_reason(self):
        order = {"status": "Delivered", "delivered_date": days_ago(5)}
        result = check_refund_policy(order)
        assert "allowed" in result
        assert "reason" in result

    def test_boundary_exactly_30_days(self):
        order = {"status": "Delivered", "delivered_date": days_ago(30)}
        result = check_refund_policy(order)
        assert result["allowed"] is True

    def test_boundary_31_days(self):
        order = {"status": "Delivered", "delivered_date": days_ago(31)}
        result = check_refund_policy(order)
        assert result["allowed"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# check_return_policy  (45-day window)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckReturnPolicy:

    def test_eligible_recent_delivery(self):
        order = {"status": "Delivered", "delivered_date": days_ago(10)}
        assert check_return_policy(order)["allowed"] is True

    def test_eligible_35_days(self):
        """35 days — outside refund window but INSIDE return window."""
        order = {"status": "Delivered", "delivered_date": days_ago(35)}
        assert check_return_policy(order)["allowed"] is True

    def test_ineligible_expired_45_days(self):
        order = {"status": "Delivered", "delivered_date": days_ago(50)}
        result = check_return_policy(order)
        assert result["allowed"] is False
        assert "expired" in result["reason"].lower()

    def test_ineligible_not_delivered(self):
        order = {"status": "Shipped", "delivered_date": None}
        assert check_return_policy(order)["allowed"] is False

    def test_boundary_exactly_45_days(self):
        order = {"status": "Delivered", "delivered_date": days_ago(45)}
        assert check_return_policy(order)["allowed"] is True

    def test_boundary_46_days(self):
        order = {"status": "Delivered", "delivered_date": days_ago(46)}
        assert check_return_policy(order)["allowed"] is False

    def test_empty_order(self):
        assert check_return_policy(None)["allowed"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# check_exchange_policy  (same rules as return)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckExchangePolicy:

    def test_eligible(self):
        order = {"status": "Delivered", "delivered_date": days_ago(15)}
        assert check_exchange_policy(order)["allowed"] is True

    def test_ineligible_expired(self):
        order = {"status": "Delivered", "delivered_date": days_ago(50)}
        assert check_exchange_policy(order)["allowed"] is False

    def test_ineligible_not_delivered(self):
        order = {"status": "Processing", "delivered_date": None}
        assert check_exchange_policy(order)["allowed"] is False

    def test_same_result_as_return_policy(self):
        """Exchange policy delegates to return policy — results must match."""
        order = {"status": "Delivered", "delivered_date": days_ago(20)}
        assert check_exchange_policy(order) == check_return_policy(order)


# ═══════════════════════════════════════════════════════════════════════════════
# policy_agent state machine
# ═══════════════════════════════════════════════════════════════════════════════

def make_state(intent: str, order_details: dict) -> dict:
    return {
        "intent": intent,
        "entities": {"order_details": order_details},
        "current_state": "POLICY_CHECK",
    }


@pytest.mark.asyncio
class TestPolicyAgent:

    async def test_refund_allowed(self):
        state = make_state("refund", {"status": "Delivered", "delivered_date": days_ago(5)})
        result = await policy_agent(state)
        pr = result["entities"]["policy_result"]
        assert pr["allowed"] is True
        assert pr["policy_type"] == "refund"
        assert result["current_state"] == "RESOLUTION"

    async def test_refund_denied_expired(self):
        state = make_state("refund", {"status": "Delivered", "delivered_date": days_ago(40)})
        result = await policy_agent(state)
        pr = result["entities"]["policy_result"]
        assert pr["allowed"] is False
        assert result["current_state"] == "RESOLUTION"

    async def test_return_allowed(self):
        state = make_state("return", {"status": "Delivered", "delivered_date": days_ago(20)})
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is True

    async def test_return_denied_not_delivered(self):
        state = make_state("return", {"status": "Shipped", "delivered_date": None})
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is False

    async def test_exchange_allowed(self):
        state = make_state("exchange", {"status": "Delivered", "delivered_date": days_ago(10)})
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is True

    async def test_cancel_allowed_when_processing(self):
        state = make_state("cancel", {"status": "Processing"})
        result = await policy_agent(state)
        pr = result["entities"]["policy_result"]
        assert pr["allowed"] is True
        assert result["current_state"] == "RESOLUTION"

    async def test_cancel_denied_when_shipped(self):
        state = make_state("cancel", {"status": "Shipped"})
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is False

    async def test_cancel_denied_when_delivered(self):
        state = make_state("cancel", {"status": "Delivered"})
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is False

    async def test_cancel_denied_already_cancelled(self):
        state = make_state("cancel", {"status": "Cancelled"})
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is False

    async def test_order_tracking_always_allowed(self):
        state = make_state("order_tracking", {"status": "Shipped"})
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is True

    async def test_general_question_no_policy_check(self):
        state = make_state("general_question", None)
        result = await policy_agent(state)
        pr = result["entities"]["policy_result"]
        assert pr["allowed"] is True
        assert pr["policy_checked"] is False

    async def test_complaint_no_policy_check(self):
        state = make_state("complaint", None)
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["policy_checked"] is False

    async def test_technical_issue_no_policy_check(self):
        state = make_state("technical_issue", None)
        result = await policy_agent(state)
        assert result["entities"]["policy_result"]["allowed"] is True

    async def test_always_transitions_to_resolution(self):
        """All intents must end in RESOLUTION state."""
        for intent in ("refund", "return", "exchange", "cancel", "order_tracking",
                        "complaint", "technical_issue", "general_question"):
            order = {"status": "Delivered", "delivered_date": days_ago(5)} if intent in (
                "refund", "return", "exchange") else {"status": "Processing"}
            state = make_state(intent, order)
            result = await policy_agent(state)
            assert result["current_state"] == "RESOLUTION", (
                f"Intent '{intent}' should move to RESOLUTION"
            )
