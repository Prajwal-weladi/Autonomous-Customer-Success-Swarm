
import pytest
from app.agents.resolution.agent import resolution_agent

class TestResolutionAgent:

    @pytest.mark.asyncio
    async def test_resolution_refund_approved(self):
        """Generates refund approved message"""
        state = {
            "intent": "refund",
            "entities": {
                "policy_result": {"allowed": True},
                "order_details": {"order_id": "123", "product": "TestItem"}
            }
        }
        
        new_state = await resolution_agent(state)
        
        assert "approved" in new_state["reply"].lower()
        assert "TestItem" in new_state["reply"]
        assert new_state["status"] == "completed"

    @pytest.mark.asyncio
    async def test_resolution_refund_denied(self):
        """Generates refund denied message"""
        state = {
            "intent": "refund",
            "entities": {
                "policy_result": {"allowed": False, "reason": "Too old"},
                "order_details": {"order_id": "123"}
            }
        }
        
        new_state = await resolution_agent(state)
        
        assert "cannot process a refund" in new_state["reply"].lower()
        assert "Too old" in new_state["reply"]

    @pytest.mark.asyncio
    async def test_resolution_tracking(self):
        """Generates tracking message"""
        state = {
            "intent": "order_tracking",
            "entities": {
                "order_details": {
                    "order_id": "123", 
                    "status": "Shipped", 
                    "product": "Item",
                    "order_date": "2023-01-01"
                }
            }
        }
        
        new_state = await resolution_agent(state)
        
        assert "is currently in transit" in new_state["reply"]

    @pytest.mark.asyncio
    async def test_resolution_unknown_intent(self):
        """Unknown intent triggers handoff"""
        state = {
            "intent": "random_intent",
            "entities": {}
        }
        
        new_state = await resolution_agent(state)
        
        assert new_state["current_state"] == "HUMAN_HANDOFF"
        assert "connect you with a human" in new_state["reply"]
