
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

class TestApiResolution:

    @patch("app.api.resolution.run_agent_llm")
    @patch("app.api.resolution.update_deal_stage")
    def test_resolve_endpoint(self, mock_crm, mock_llm, client: TestClient):
        """Test /resolve endpoint integration"""
        mock_llm.return_value = {
            "action": "refund",
            "message": "Refund processed",
            "refund_amount": 50
        }
        
        payload = {
            "order_id": "123",
            "intent": "refund",
            "amount": 50,
            "cancel_allowed": True
        }
        
        res = client.post("/resolve", json=payload)
        
        assert res.status_code == 200
        assert res.json()["action"] == "refund"
        # Verify CRM called twice (CANCELLED and REFUND_DONE)
        assert mock_crm.call_count == 2
