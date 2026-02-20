
import pytest
from unittest.mock import patch, MagicMock
from app.agents.resolution.core.llm.Resolution_agent_llm import run_agent_llm
from app.agents.resolution.app.schemas.model import ResolutionInput

class TestResolutionLLM:

    @pytest.fixture
    def mock_input(self):
        return ResolutionInput(
            order_id="123",
            intent="refund",
            product="Test Product",
            amount=100,
            cancel_allowed=True
        )

    @patch("app.agents.resolution.core.llm.Resolution_agent_llm.generate_return_label")
    def test_refund_execution(self, mock_label, mock_input):
        """Test refund execution path"""
        res = run_agent_llm(mock_input)
        
        assert res["action"] == "cancel"
        assert res["refund_amount"] == 100
        assert "Refund Initiated" in res["message"]

    def test_tracking_execution(self):
        """Test tracking execution path"""
        input_data = ResolutionInput(
            order_id="123",
            intent="order_tracking",
            status="Shipped"
        )
        res = run_agent_llm(input_data)
        
        assert res["action"] == "order_tracking"
        assert res["status"] == "Shipped"

    @patch("app.agents.resolution.core.llm.Resolution_agent_llm.generate_return_label")
    def test_return_approved(self, mock_label, mock_input):
        """Test return approved path"""
        mock_input.intent = "return"
        mock_input.exchange_allowed = True # Means return allowed too
        mock_label.return_value = "label.pdf"
        
        res = run_agent_llm(mock_input)
        
        assert res["action"] == "return"
        assert "label.pdf" in res["return_label_url"]

    def test_return_denied(self, mock_input):
        """Test return denied path"""
        mock_input.intent = "return"
        mock_input.exchange_allowed = False
        mock_input.reason = "Policy violation"
        
        res = run_agent_llm(mock_input)
        
        assert res["action"] == "return_deny"
        assert "Policy violation" in res["reason"]
