
import pytest
# Mock streamlit again
import sys
from unittest.mock import MagicMock
sys.modules["streamlit"] = MagicMock()

from frontend.components.chat import format_resolution_message, format_pipeline_metadata

class TestChatFormatting:

    def test_format_resolution_refund_approved(self):
        pipeline_res = {
            "resolution_output": {
                "action": "refund",
                "refund_amount": 100,
                "message": "Refund processed"
            },
            "triage_output": {}, "database_output": {}, "policy_output": {}
        }
        
        msg = format_resolution_message(pipeline_res)
        assert "Refund processed" in msg
        assert "Refund Amount: ₹100" in msg

    def test_format_resolution_return_label(self):
        pipeline_res = {
            "resolution_output": {
                "action": "return",
                "return_label_url": "http://label.pdf",
                "message": "Return approved"
            },
            "triage_output": {}, "database_output": {}, "policy_output": {}
        }
        
        msg = format_resolution_message(pipeline_res)
        assert "Return approved" in msg
        assert "[**Download Return Label**](http://label.pdf)" in msg

    def test_format_metadata(self):
        pipeline_res = {
            "triage_output": {"intent": "refund", "confidence": 0.95},
            "database_output": {"order_found": True},
            "policy_output": {"policy_checked": True, "allowed": True},
            "resolution_output": {"action": "cancel"}
        }
        
        meta = format_pipeline_metadata(pipeline_res)
        assert "Intent: refund" in meta
        assert "Order Found" in meta
        assert "Policy: ✅ Allowed" in meta
        assert "Action: cancel" in meta
