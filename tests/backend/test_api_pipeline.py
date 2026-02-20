
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class TestApiPipeline:
    
    # We can mock the agent functions to ensure pipeline flow is correct
    # without re-testing the agent logic itself (covered in unit tests)
    
    @patch("app.api.message.run_triage")
    @patch("app.api.message.fetch_order_details")
    @patch("app.api.message.check_refund_policy")
    @patch("app.api.message.run_agent_llm")
    def test_pipeline_success_flow(
        self, 
        mock_llm, 
        mock_policy, 
        mock_db, 
        mock_triage, 
        client: TestClient
    ):
        """Test complete successful pipeline execution"""
        
        # 1. Triage
        mock_triage.return_value = {
            "intent": "refund", 
            "urgency": "normal", 
            "order_id": "123",
            "confidence": 0.9,
            "user_issue": "Broken item"
        }
        
        # 2. DB
        mock_db.return_value = {
            "order_found": True,
            "order_details": {"order_id": "123", "status": "Delivered", "amount": 100}
        }
        
        # 3. Policy
        mock_policy.return_value = {"allowed": True, "reason": "OK"}
        
        # 4. Resolution
        mock_llm.return_value = {
            "action": "cancel",
            "message": "Refund processed",
            "refund_amount": 100
        }
        
        res = client.post("/v1/pipeline", json={"conversation_id": "pipe-1", "message": "refund order 123"})
        
        assert res.status_code == 200
        data = res.json()
        
        assert data["triage_output"]["intent"] == "refund"
        assert data["database_output"]["order_found"] is True
        assert data["policy_output"]["allowed"] is True
        assert data["resolution_output"]["action"] == "cancel"
        
    @patch("app.api.message.run_triage")
    def test_pipeline_missing_order_id(self, mock_triage, client: TestClient):
        """Test pipeline stops if order ID missing for action intent"""
        
        mock_triage.return_value = {
            "intent": "refund", 
            "order_id": None, # Missing
            "urgency": "normal"
        }
        
        res = client.post("/v1/pipeline", json={"conversation_id": "pipe-2", "message": "refund please"})
        
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "awaiting_input"
        assert "Order ID required" in data["resolution_output"]["reason"]
