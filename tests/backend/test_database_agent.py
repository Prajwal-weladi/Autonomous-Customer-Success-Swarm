
import pytest
from unittest.mock import patch, MagicMock
from app.agents.database.agent import database_agent

class TestDatabaseAgent:

    @pytest.mark.asyncio
    async def test_no_order_id_handoff(self):
        """Action intent without order ID triggers handoff"""
        state = {
            "intent": "refund",
            "entities": {} # No order_id
        }
        
        new_state = await database_agent(state)
        
        assert new_state["current_state"] == "HUMAN_HANDOFF"
        assert "status" in new_state and new_state["status"] == "handoff" 

    @pytest.mark.asyncio
    async def test_no_order_id_bypass(self):
        """General question without order ID bypasses DB"""
        state = {
            "intent": "general_question",
            "entities": {} 
        }
        
        new_state = await database_agent(state)
        
        assert new_state["current_state"] == "POLICY_CHECK"
        assert new_state["order_details"] is None

    @pytest.mark.asyncio
    @patch("app.agents.database.agent.fetch_order_details")
    async def test_order_found(self, mock_fetch):
        """Order found updates state"""
        mock_fetch.return_value = {
            "order_found": True,
            "order_details": {"order_id": "123", "status": "Shipped", "amount": 100}
        }
        
        state = {
            "intent": "track",
            "entities": {"order_id": "123"}
        }
        
        new_state = await database_agent(state)
        
        assert new_state["current_state"] == "POLICY_CHECK"
        assert new_state["entities"]["order_details"]["status"] == "Shipped"
        assert new_state["entities"]["order_details"]["amount"] == 100

    @pytest.mark.asyncio
    @patch("app.agents.database.agent.fetch_order_details")
    async def test_order_not_found(self, mock_fetch):
        """Order not found ends conversation"""
        mock_fetch.return_value = {
            "order_found": False,
            "error": "Not found"
        }
        
        state = {
            "intent": "track",
            "entities": {"order_id": "999"}
        }
        
        new_state = await database_agent(state)
        
        assert new_state["current_state"] == "COMPLETED"
        assert "not found" in new_state["reply"]
