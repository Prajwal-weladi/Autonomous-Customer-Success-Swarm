
import pytest
from unittest.mock import patch, MagicMock
from frontend.api.client import send_message, send_pipeline_message

class TestFrontendClient:
    
    @patch("frontend.api.client.requests.post")
    def test_send_pipeline_message(self, mock_post):
        """Test sending pipeline message"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "completed"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        cid = "123"
        msg = "hello"
        
        res = send_pipeline_message(cid, msg)
        
        assert res["status"] == "completed"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["conversation_id"] == cid
        assert "pipeline" in args[0]
