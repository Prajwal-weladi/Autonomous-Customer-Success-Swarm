"""
Tests for the database agent state machine.
fetch_order_details is mocked — we test the agent's branching logic:
  Case 1: No order ID + no-order-needed intent
  Case 2: No order ID + order-needed intent
  Case 3: Order not found
  Case 4: Order found → populate state and move to POLICY_CHECK
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.database.agent import database_agent


def make_state(order_id=None, intent="order_tracking") -> dict:
    return {
        "intent": intent,
        "entities": {"order_id": order_id, "query": "test"},
        "current_state": "DATA_FETCH",
    }


SAMPLE_ORDER = {
    "order_id": "12345",
    "product": "Wireless Headphones",
    "status": "Delivered",
    "order_date": "2026-01-20",
    "delivered_date": "2026-02-05",
    "amount": 2199,
}


# ═══════════════════════════════════════════════════════════════════════════════
# database_agent state machine
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestDatabaseAgent:

    # ── Case 1: No order ID, intent doesn't need one ─────────────────────────
    async def test_general_question_skips_db(self):
        state = make_state(order_id=None, intent="general_question")
        result = await database_agent(state)
        assert result["entities"]["order_details"] is None
        assert result["current_state"] == "POLICY_CHECK"

    async def test_technical_issue_skips_db(self):
        state = make_state(order_id=None, intent="technical_issue")
        result = await database_agent(state)
        assert result["entities"]["order_details"] is None
        assert result["current_state"] == "POLICY_CHECK"

    # ── Case 2: No order ID, intent requires one ─────────────────────────────
    @pytest.mark.parametrize("intent", ["refund", "return", "exchange", "cancel", "order_tracking"])
    async def test_missing_order_id_sets_error(self, intent):
        state = make_state(order_id=None, intent=intent)
        result = await database_agent(state)
        assert result["current_state"] in ("HUMAN_HANDOFF", "COMPLETED")
        assert "reply" in result

    # ── Case 3: Order not found ───────────────────────────────────────────────
    @patch("app.agents.database.agent.fetch_order_details")
    async def test_order_not_found(self, mock_fetch):
        mock_fetch.return_value = {"order_found": False}
        state = make_state(order_id="99999", intent="order_tracking")
        result = await database_agent(state)
        assert result["current_state"] == "COMPLETED"
        assert "not found" in result["reply"].lower() or "99999" in result["reply"]

    # ── Case 4: Order found ───────────────────────────────────────────────────
    @patch("app.agents.database.agent.fetch_order_details")
    async def test_order_found_populates_state(self, mock_fetch):
        mock_fetch.return_value = {"order_found": True, "order_details": SAMPLE_ORDER}
        state = make_state(order_id="12345", intent="order_tracking")
        result = await database_agent(state)
        assert result["entities"]["order_details"] == SAMPLE_ORDER
        assert result["current_state"] == "POLICY_CHECK"

    @patch("app.agents.database.agent.fetch_order_details")
    async def test_amount_defaults_to_zero_if_missing(self, mock_fetch):
        order_no_amount = {k: v for k, v in SAMPLE_ORDER.items() if k != "amount"}
        mock_fetch.return_value = {"order_found": True, "order_details": order_no_amount}
        state = make_state(order_id="12345", intent="refund")
        result = await database_agent(state)
        assert result["entities"]["order_details"]["amount"] == 0

    @patch("app.agents.database.agent.fetch_order_details")
    async def test_order_details_also_set_at_top_level(self, mock_fetch):
        """order_details must be set both in entities and at state top-level."""
        mock_fetch.return_value = {"order_found": True, "order_details": SAMPLE_ORDER}
        state = make_state(order_id="12345", intent="return")
        result = await database_agent(state)
        assert result["order_details"] == SAMPLE_ORDER

    @patch("app.agents.database.agent.fetch_order_details")
    async def test_fetch_called_with_correct_order_id(self, mock_fetch):
        mock_fetch.return_value = {"order_found": True, "order_details": SAMPLE_ORDER}
        state = make_state(order_id="99911", intent="refund")
        await database_agent(state)
        mock_fetch.assert_called_once_with("99911")
