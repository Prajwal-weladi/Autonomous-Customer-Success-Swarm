
import pytest
from datetime import datetime, timedelta
from app.agents.policy.agent import check_refund_policy, check_return_policy, check_exchange_policy, get_policy_information, policy_agent

class TestPolicyAgent:

    # --- 1. Policy Logic Tests ---
    
    def test_refund_policy_valid(self):
        """Valid refund: delivered + within 30 days"""
        order = {
            "status": "Delivered",
            "delivered_date": (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
        }
        res = check_refund_policy(order)
        assert res["allowed"] is True

    def test_refund_policy_expired(self):
        """Expired refund: delivered 31 days ago"""
        order = {
            "status": "Delivered",
            "delivered_date": (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
        }
        res = check_refund_policy(order)
        assert res["allowed"] is False
        assert "expired" in res["reason"].lower()

    def test_return_policy_valid(self):
        """Valid return: delivered + within 45 days"""
        order = {
            "status": "Delivered",
            "delivered_date": (datetime.now() - timedelta(days=44)).strftime("%Y-%m-%d")
        }
        res = check_return_policy(order)
        assert res["allowed"] is True

    def test_cancel_policy(self):
        """Cancel policy handled inside agent function"""
        # Logic is embedded in policy_agent, tested below
        pass

    # --- 2. Information Retrieval ---

    def test_get_policy_info(self):
        """Test retrieving specific and all policy info"""
        info = get_policy_information("refund")
        assert "Refund Policy" in info["message"]
        
        all_info = get_policy_information()
        assert "Refund Policy" in all_info["message"]
        assert "Return Policy" in all_info["message"]

    # --- 3. Agent Execution Tests ---

    @pytest.mark.asyncio
    async def test_policy_agent_cancel_denied(self):
        """Cancel denied if shipped"""
        state = {
            "intent": "cancel",
            "entities": {
                "order_details": {"status": "Shipped", "order_id": "123"}
            }
        }
        
        new_state = await policy_agent(state)
        
        res = new_state["entities"]["policy_result"]
        assert res["allowed"] is False
        assert res["policy_type"] == "cancel"
        assert "already been shipped" in res["reason"].lower()

    @pytest.mark.asyncio
    async def test_policy_agent_cancel_allowed(self):
        """Cancel allowed if processing"""
        state = {
            "intent": "cancel",
            "entities": {
                "order_details": {"status": "Processing", "order_id": "123"}
            }
        }
        
        new_state = await policy_agent(state)
        
        res = new_state["entities"]["policy_result"]
        assert res["allowed"] is True
        assert res["policy_type"] == "cancel"

    @pytest.mark.asyncio
    async def test_policy_agent_bypass(self):
        """Tracking bypasses policy check"""
        state = {
            "intent": "order_tracking",
            "entities": {"order_details": {"status": "Shipped"}}
        }
        
        new_state = await policy_agent(state)
        
        res = new_state["entities"]["policy_result"]
        assert res["allowed"] is True
        assert res["policy_checked"] is False
