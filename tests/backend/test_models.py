
import pytest
from app.api.message import MessageRequest, MessageResponse, TriageOutput, DatabaseOutput

class TestPydanticModels:

    def test_message_request(self):
        req = MessageRequest(conversation_id="123", message="hi")
        assert req.conversation_id == "123"
        
    def test_triage_output(self):
        out = TriageOutput(
            intent="refund", 
            urgency="high", 
            order_id="123", 
            confidence=0.9, 
            user_issue="issue"
        )
        assert out.order_id == "123"
        # Optional field
        out2 = TriageOutput(
             intent="refund", 
            urgency="high", 
            order_id=None, 
            confidence=0.9, 
            user_issue="issue"           
        )
        assert out2.order_id is None
