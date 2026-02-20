
import pytest
from unittest.mock import patch, MagicMock
from app.agents.triage.agent import extract_order_id, rule_based_intent, rule_based_urgency, run_triage, triage_agent

class TestTriageAgent:

    # --- 1. Order ID Extraction ---
    
    @pytest.mark.parametrize("text, expected", [
        ("my order id is 12345", "12345"),
        ("order #98765 please", "98765"),
        ("status for #55555", "55555"),
        ("it's 11223", "11223"),
        ("just checking 12345678", "12345678"),
        ("no order here", None),
        ("order id is not provided", None), # Placeholder text check (implicit via regex)
    ])
    def test_extract_order_id(self, text, expected):
        assert extract_order_id(text) == expected

    # --- 2. Rule-Based Intent ---
    
    @pytest.mark.parametrize("text, expected_intent", [
        ("what is your refund policy?", "policy_info"),
        ("i want to cancel my order", "cancel"),
        ("track my package", "order_tracking"),
        ("return this item", "return"),
        ("exchange for size M", "exchange"),
        ("this is terrible service", "complaint"),
        ("website is broken", "technical_issue"),
        ("hello there", None), # Fallback to None/unknown
    ])
    def test_rule_based_intent(self, text, expected_intent):
        assert rule_based_intent(text) == expected_intent

    # --- 3. Urgency Detection ---

    @pytest.mark.parametrize("text, expected_urgency", [
        ("i need this asap", "high"),
        ("urgent help needed", "high"),
        ("this is the worst experience", "high"), # Complaint keyword
        ("just wondering about shipping", "normal"),
    ])
    def test_rule_based_urgency(self, text, expected_urgency):
        assert rule_based_urgency(text) == expected_urgency

    # --- 4. Main Triage Runner (Mocked LLM) ---
    
    def test_run_triage_llm_success(self, mock_dependencies):
        """Test triage with successful LLM JSON response"""
        mock_ollama = mock_dependencies["ollama"]
        # Mock correct JSON return
        mock_ollama.chat.return_value = {
            "message": {
                "content": '{"intent": "refund", "urgency": "high", "order_id": "999", "confidence": 0.95}'
            }
        }
        
        result = run_triage("refund order 999 now")
        
        assert result["intent"] == "refund"
        assert result["urgency"] == "high"
        assert result["order_id"] == "999"
        assert result["confidence"] == 0.95

    def test_run_triage_llm_failure_fallback(self, mock_dependencies):
        """Test triage falling back to rules when LLM fails"""
        mock_ollama = mock_dependencies["ollama"]
        # Mock malformed JSON
        mock_ollama.chat.return_value = {
            "message": {
                "content": "Not JSON"
            }
        }
        
        # Should detect "cancel" from rules
        result = run_triage("cancel my order")
        
        assert result["intent"] == "cancel"
        assert result["confidence"] == 0.50 # Low confidence fallback

    # --- 5. Triage Agent State Transition ---

    @pytest.mark.asyncio
    async def test_triage_agent_execution(self, mock_dependencies):
        """Test full triage agent updating state"""
        mock_ollama = mock_dependencies["ollama"]
        mock_ollama.chat.return_value = {
            "message": {
                "content": '{"intent": "return", "urgency": "normal", "order_id": "555"}'
            }
        }
        
        initial_state = {"user_message": "return order 555"}
        new_state = await triage_agent(initial_state)
        
        assert new_state["intent"] == "return"
        assert new_state["entities"]["order_id"] == "555"
        assert new_state["current_state"] == "DATA_FETCH"
        assert "triage_summary" in new_state["entities"]

    @pytest.mark.asyncio
    async def test_triage_agent_empty_message(self):
        """Test handling of empty message"""
        state = {"user_message": ""}
        new_state = await triage_agent(state)
        
        assert new_state["current_state"] == "HUMAN_HANDOFF"
        assert "Empty user message" in new_state["last_error"]
