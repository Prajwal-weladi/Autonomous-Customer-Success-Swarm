import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.triage.agent import (
    run_triage, 
    triage_agent,
    extract_order_id,
    rule_based_intent
)

# ═══════════════════════════════════════════════════════════════════════════════
# run_triage with LLM mocks
# ═══════════════════════════════════════════════════════════════════════════════

@patch("app.agents.triage.agent.OLLAMA_AVAILABLE", True)
@patch("app.agents.triage.agent.ollama.chat")
def test_run_triage_llm_valid_json(mock_chat):
    mock_chat.return_value = {
        "message": {
            "content": json.dumps({
                "intent": "refund",
                "urgency": "high",
                "order_id": "12345",
                "confidence": 0.9,
                "user_issue": "Broken item"
            })
        }
    }
    result = run_triage("I want a refund for 12345, it is broken")
    assert result["intent"] == "refund"
    assert result["urgency"] == "high"
    assert result["order_id"] == "12345"
    assert result["confidence"] == 0.9

@patch("app.agents.triage.agent.OLLAMA_AVAILABLE", True)
@patch("app.agents.triage.agent.ollama.chat")
def test_run_triage_llm_markdown_json(mock_chat):
    mock_chat.return_value = {
        "message": {
            "content": "```json\n" + json.dumps({
                "intent": "return",
                "urgency": "normal",
                "order_id": "98765",
                "confidence": 0.8
            }) + "\n```"
        }
    }
    result = run_triage("return 98765")
    assert result["intent"] == "return"
    assert result["order_id"] == "98765"

@patch("app.agents.triage.agent.OLLAMA_AVAILABLE", True)
@patch("app.agents.triage.agent.ollama.chat")
def test_run_triage_llm_invalid_json(mock_chat):
    mock_chat.return_value = {"message": {"content": "This is not json"}}
    result = run_triage("I have a general question")
    assert result["intent"] == "general_question"
    assert result["confidence"] == 0.5 # FALLBACK_CONFIDENCE

@patch("app.agents.triage.agent.OLLAMA_AVAILABLE", True)
@patch("app.agents.triage.agent.ollama.chat", side_effect=Exception("API Error"))
def test_run_triage_llm_exception(mock_chat):
    result = run_triage("I have a general question")
    assert result["intent"] == "general_question"
    assert result["confidence"] == 0.5

@patch("app.agents.triage.agent.OLLAMA_AVAILABLE", False)
def test_run_triage_no_ollama():
    result = run_triage("cancel my order 12345")
    assert result["intent"] == "cancel"
    assert result["order_id"] == "12345"

@patch("app.agents.triage.agent.OLLAMA_AVAILABLE", True)
@patch("app.agents.triage.agent.ollama.chat")
def test_run_triage_llm_invalid_order_id_placeholder(mock_chat):
    mock_chat.return_value = {
        "message": {
            "content": json.dumps({"intent": "refund", "order_id": "not provided"})
        }
    }
    result = run_triage("refund please")
    assert result["order_id"] is None

@patch("app.agents.triage.agent.OLLAMA_AVAILABLE", True)
@patch("app.agents.triage.agent.ollama.chat")
def test_run_triage_history(mock_chat):
    mock_chat.return_value = {
        "message": {"content": json.dumps({"intent": "refund"})}
    }
    history = [{"role": "assistant", "content": "What is the issue?"}]
    result = run_triage("I need a refund", history)
    assert result["intent"] == "refund"

# ═══════════════════════════════════════════════════════════════════════════════
# triage_agent async wrapper
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_triage_agent_empty_message():
    state = {"user_message": ""}
    res = await triage_agent(state)
    assert res["current_state"] == "HUMAN_HANDOFF"
    assert res["last_error"] == "Empty user message"

@pytest.mark.asyncio
async def test_triage_agent_awaiting_order_id_success():
    state = {
        "user_message": "123456",
        "awaiting_order_id": True,
        "intent": "refund",
        "entities": {}
    }
    res = await triage_agent(state)
    assert res["current_state"] == "DATA_FETCH"
    assert res["entities"]["order_id"] == "123456"
    assert res["awaiting_order_id"] is False

@pytest.mark.asyncio
async def test_triage_agent_awaiting_order_id_fail():
    state = {
        "user_message": "still no idea",
        "awaiting_order_id": True,
        "intent": "refund"
    }
    res = await triage_agent(state)
    assert res["current_state"] == "COMPLETED"
    assert "reply" in res
    assert "couldn't find" in res["reply"].lower()

@pytest.mark.asyncio
@patch("app.agents.triage.agent.run_triage")
async def test_triage_agent_normal_flow(mock_run_triage):
    mock_run_triage.return_value = {
        "intent": "refund",
        "urgency": "normal",
        "order_id": "12345",
        "confidence": 0.95,
        "user_issue": "Needs refund"
    }
    state = {"user_message": "refund please 12345"}
    res = await triage_agent(state)
    
    assert res["current_state"] == "DATA_FETCH"
    assert res["intent"] == "refund"
    assert res["urgency"] == "normal"
    assert res["entities"]["order_id"] == "12345"
    assert "triage_summary" in res["entities"]
    assert res["entities"]["triage_confidence"] == 0.95
